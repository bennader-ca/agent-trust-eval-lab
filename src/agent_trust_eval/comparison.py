"""Strict cross-run comparison reports for bounded public findings."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import sys


class ComparisonError(ValueError):
    """Raised when reports cannot support a like-for-like comparison."""


@dataclass(frozen=True)
class ComparableRun:
    """Whitelisted evidence extracted from one full report."""

    report_sha256: str
    generated_at: str
    name: str
    fingerprint: str
    provider: str
    model: str
    model_version: str
    inference_policy: str
    safeguards: tuple[str, ...]
    repeats: int
    total_trials: int
    completed_trials: int
    passed_trials: int
    pass_rate: float | None
    false_promotions: int
    false_promotion_rate: float | None
    false_refusals: int
    false_refusal_rate: float | None
    flipped_cases: int
    flip_rate: float | None
    provider_errors: int
    permission_recommendation: str
    normalized_usage: dict[str, int]


def _object(value: object, location: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ComparisonError(f"{location} must be an object")
    return value


def _string(value: object, location: str) -> str:
    if not isinstance(value, str) or not value:
        raise ComparisonError(f"{location} must be a non-empty string")
    return value


def _integer(value: object, location: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ComparisonError(f"{location} must be a non-negative integer")
    return value


def _positive_integer(value: object, location: str) -> int:
    result = _integer(value, location)
    if result < 1:
        raise ComparisonError(f"{location} must be a positive integer")
    return result


def _rate(value: object, location: str) -> float | None:
    if value is None:
        return None
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 <= value <= 1:
        raise ComparisonError(f"{location} must be null or a number from 0 through 1")
    return float(value)


def _load_report(path: Path) -> tuple[dict[str, object], ComparableRun]:
    try:
        raw_bytes = path.read_bytes()
    except OSError as exc:
        raise ComparisonError(f"cannot read report: {path}") from exc
    try:
        report = json.loads(raw_bytes)
    except json.JSONDecodeError as exc:
        raise ComparisonError(
            f"invalid JSON in {path}: line {exc.lineno}, column {exc.colno}"
        ) from exc
    report = _object(report, str(path))
    if report.get("schema_version") != "2.0":
        raise ComparisonError(f"{path} must be an Agent Trust Eval report with schema 2.0")

    suite = _object(report.get("suite"), f"{path}.suite")
    system = _object(report.get("system_under_test"), f"{path}.system_under_test")
    manifest = _object(system.get("manifest"), f"{path}.system_under_test.manifest")
    execution = _object(report.get("execution"), f"{path}.execution")
    summary = _object(report.get("summary"), f"{path}.summary")
    recommendation = _object(
        report.get("permission_recommendation"), f"{path}.permission_recommendation"
    )
    _object(report.get("calibration_policy"), f"{path}.calibration_policy")

    safeguards_value = manifest.get("safeguards")
    if not isinstance(safeguards_value, list) or any(
        not isinstance(item, str) or not item for item in safeguards_value
    ):
        raise ComparisonError(f"{path}.system_under_test.manifest.safeguards must be strings")

    usage_envelope = execution.get("normalized_usage", {})
    usage_envelope = _object(usage_envelope, f"{path}.execution.normalized_usage")
    usage_totals = _object(
        usage_envelope.get("totals", {}), f"{path}.execution.normalized_usage.totals"
    )
    normalized_usage: dict[str, int] = {}
    for key, value in usage_totals.items():
        if not isinstance(key, str):
            raise ComparisonError(f"{path}.execution.normalized_usage.totals keys must be strings")
        normalized_usage[key] = _integer(
            value, f"{path}.execution.normalized_usage.totals.{key}"
        )

    comparable = ComparableRun(
        report_sha256=f"sha256:{sha256(raw_bytes).hexdigest()}",
        generated_at=_string(report.get("generated_at"), f"{path}.generated_at"),
        name=_string(manifest.get("name"), f"{path}.system_under_test.manifest.name"),
        fingerprint=_string(system.get("fingerprint"), f"{path}.system_under_test.fingerprint"),
        provider=_string(manifest.get("provider"), f"{path}.system_under_test.manifest.provider"),
        model=_string(manifest.get("model"), f"{path}.system_under_test.manifest.model"),
        model_version=_string(
            manifest.get("model_version"), f"{path}.system_under_test.manifest.model_version"
        ),
        inference_policy=_string(
            manifest.get("inference_policy"),
            f"{path}.system_under_test.manifest.inference_policy",
        ),
        safeguards=tuple(safeguards_value),
        repeats=_positive_integer(execution.get("repeats"), f"{path}.execution.repeats"),
        total_trials=_integer(summary.get("total_trials"), f"{path}.summary.total_trials"),
        completed_trials=_integer(
            summary.get("completed_trials"), f"{path}.summary.completed_trials"
        ),
        passed_trials=_integer(summary.get("passed_trials"), f"{path}.summary.passed_trials"),
        pass_rate=_rate(summary.get("pass_rate"), f"{path}.summary.pass_rate"),
        false_promotions=_integer(
            summary.get("false_promotions"), f"{path}.summary.false_promotions"
        ),
        false_promotion_rate=_rate(
            summary.get("false_promotion_rate"), f"{path}.summary.false_promotion_rate"
        ),
        false_refusals=_integer(
            summary.get("false_refusals"), f"{path}.summary.false_refusals"
        ),
        false_refusal_rate=_rate(
            summary.get("false_refusal_rate"), f"{path}.summary.false_refusal_rate"
        ),
        flipped_cases=_integer(summary.get("flipped_cases"), f"{path}.summary.flipped_cases"),
        flip_rate=_rate(summary.get("flip_rate"), f"{path}.summary.flip_rate"),
        provider_errors=_integer(
            summary.get("provider_errors"), f"{path}.summary.provider_errors"
        ),
        permission_recommendation=_string(
            recommendation.get("level"), f"{path}.permission_recommendation.level"
        ),
        normalized_usage=dict(sorted(normalized_usage.items())),
    )
    return report, comparable


def _comparison_basis(report: dict[str, object]) -> dict[str, object]:
    suite = _object(report["suite"], "suite")
    case_aggregates = report.get("case_aggregates")
    if not isinstance(case_aggregates, list):
        raise ComparisonError("case_aggregates must be an array")
    case_ids = [
        _string(_object(case, f"case_aggregates[{index}]").get("id"), f"case_aggregates[{index}].id")
        for index, case in enumerate(case_aggregates)
    ]
    if len(case_ids) != suite.get("case_count"):
        raise ComparisonError("case_aggregates must match suite.case_count")
    case_ids_sha256 = sha256(
        json.dumps(case_ids, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "suite": {
            "schema_version": suite.get("schema_version"),
            "name": suite.get("name"),
            "workflow": suite.get("workflow"),
            "version": suite.get("version"),
            "case_count": suite.get("case_count"),
            "case_ids_sha256": f"sha256:{case_ids_sha256}",
        },
        "calibration_policy": report["calibration_policy"],
    }


def _run_dict(run: ComparableRun) -> dict[str, object]:
    return {
        "report_sha256": run.report_sha256,
        "generated_at": run.generated_at,
        "name": run.name,
        "fingerprint": run.fingerprint,
        "provider": run.provider,
        "model": run.model,
        "model_version": run.model_version,
        "inference_policy": run.inference_policy,
        "safeguards": list(run.safeguards),
        "repeats": run.repeats,
        "total_trials": run.total_trials,
        "completed_trials": run.completed_trials,
        "passed_trials": run.passed_trials,
        "pass_rate": run.pass_rate,
        "false_promotions": run.false_promotions,
        "false_promotion_rate": run.false_promotion_rate,
        "false_refusals": run.false_refusals,
        "false_refusal_rate": run.false_refusal_rate,
        "flipped_cases": run.flipped_cases,
        "flip_rate": run.flip_rate,
        "provider_errors": run.provider_errors,
        "permission_recommendation": run.permission_recommendation,
        "normalized_usage": run.normalized_usage,
    }


def compare_reports(report_paths: list[Path], output_dir: Path) -> tuple[Path, Path]:
    """Validate compatible reports and write whitelisted JSON and Markdown evidence."""

    if len(report_paths) < 2:
        raise ComparisonError("comparison requires at least two report files")
    loaded = [_load_report(path.resolve()) for path in report_paths]
    hashes = [run.report_sha256 for _, run in loaded]
    if len(hashes) != len(set(hashes)):
        raise ComparisonError("comparison inputs contain the same report more than once")

    basis = _comparison_basis(loaded[0][0])
    for index, (report, _) in enumerate(loaded[1:], 2):
        if _comparison_basis(report) != basis:
            raise ComparisonError(
                f"report {index} does not match the first report's suite and calibration policy"
            )

    runs = [run for _, run in loaded]
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    comparison = {
        "schema_version": "1.0",
        "generated_at": generated_at,
        "comparison_boundary": (
            "Policy-relative evidence for pinned configurations; not a safety certification "
            "or universal model ranking."
        ),
        "basis": basis,
        "run_count": len(runs),
        "runs": [_run_dict(run) for run in runs],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "comparison.json"
    markdown_path = output_dir / "comparison.md"
    json_path.write_text(
        json.dumps(comparison, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    markdown_path.write_text(
        _markdown_comparison(runs, basis, generated_at), encoding="utf-8"
    )
    return json_path, markdown_path


def _percentage(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.0%}"


def _markdown_comparison(
    runs: list[ComparableRun], basis: dict[str, object], generated_at: str
) -> str:
    suite = _object(basis["suite"], "basis.suite")
    lines = [
        "# Agent Trust Eval Comparison",
        "",
        "> Policy-relative evidence for pinned configurations. This is not a safety certification or universal model ranking.",
        "",
        f"- Workflow: <code>{escape(str(suite['workflow']))}</code>",
        f"- Suite: <code>{escape(str(suite['name']))} {escape(str(suite['version']))}</code>",
        f"- Cases: {suite['case_count']}",
        f"- Runs: {len(runs)}",
        f"- Generated: `{generated_at}`",
        "",
        "## Evidence comparison",
        "",
        "| # | Configuration | Provider / model | Trials | Pass rate | Unsafe promotions | False refusals | Flipped cases | Errors | Permission |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for index, run in enumerate(runs, 1):
        lines.append(
            f"| {index} | <code>{escape(run.name)}</code> | "
            f"{escape(run.provider)} / <code>{escape(run.model)}</code> | "
            f"{run.completed_trials}/{run.total_trials} | {_percentage(run.pass_rate)} | "
            f"{run.false_promotions} ({_percentage(run.false_promotion_rate)}) | "
            f"{run.false_refusals} ({_percentage(run.false_refusal_rate)}) | "
            f"{run.flipped_cases} ({_percentage(run.flip_rate)}) | {run.provider_errors} | "
            f"<code>{escape(run.permission_recommendation)}</code> |"
        )

    lines.extend(
        [
            "",
            "## Configuration identity",
            "",
            "| # | Fingerprint | Model version | Inference policy | Safeguards |",
            "|---:|---|---|---|---|",
        ]
    )
    for index, run in enumerate(runs, 1):
        safeguards = ", ".join(run.safeguards) or "none"
        lines.append(
            f"| {index} | <code>{escape(run.fingerprint)}</code> | "
            f"<code>{escape(run.model_version)}</code> | "
            f"<code>{escape(run.inference_policy)}</code> | {escape(safeguards)} |"
        )

    usage_keys = sorted({key for run in runs for key in run.normalized_usage})
    if usage_keys:
        lines.extend(
            [
                "",
                "## Normalized token usage",
                "",
                "Missing counters remain `n/a`; vendor-native usage stays in each source report.",
                "",
                "| # | " + " | ".join(f"<code>{escape(key)}</code>" for key in usage_keys) + " |",
                "|---:|" + "---:|" * len(usage_keys),
            ]
        )
        for index, run in enumerate(runs, 1):
            values = [str(run.normalized_usage.get(key, "n/a")) for key in usage_keys]
            lines.append(f"| {index} | " + " | ".join(values) + " |")

    lines.extend(
        [
            "",
            "## Source integrity",
            "",
            "| # | Source report SHA-256 | Generated |",
            "|---:|---|---|",
        ]
    )
    for index, run in enumerate(runs, 1):
        lines.append(
            f"| {index} | <code>{escape(run.report_sha256)}</code> | "
            f"<code>{escape(run.generated_at)}</code> |"
        )
    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            "Permission labels are comparable here because every input report uses the same suite and calibration policy. Differences can still arise from any fingerprinted configuration field, provider transport, vendor safety layer, or run date. This artifact does not isolate the model as the cause and does not name an overall winner.",
            "",
        ]
    )
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-trust-compare",
        description="Compare compatible Agent Trust Eval report v2 files without raw trial content.",
    )
    parser.add_argument("reports", nargs="+", type=Path, help="two or more report.json files")
    parser.add_argument(
        "--output", type=Path, default=Path("reports/comparison"), help="output directory"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        json_path, markdown_path = compare_reports(args.reports, args.output.resolve())
    except (ComparisonError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"Compared {len(args.reports)} compatible reports")
    print(f"JSON comparison: {json_path}")
    print(f"Markdown comparison: {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
