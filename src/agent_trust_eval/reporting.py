"""Machine-readable and human-readable authority-calibration reports."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from html import escape
from pathlib import Path

from .aggregation import (
    CaseAggregate,
    EvidenceMetrics,
    TrialResult,
    aggregate_trials,
    grouped_metrics,
    summarize_trials,
)
from .calibration import (
    CalibrationPolicy,
    GateResult,
    LevelAssessment,
    PermissionRecommendation,
    calibration_policy_dict,
)
from .manifest import SystemUnderTest, system_under_test_dict
from .models import EvalSuite


def _code_block(value: str) -> list[str]:
    """Render untrusted text as escaped indented code, never active Markdown/HTML."""

    lines = value.splitlines() or [""]
    return [f"    {escape(line, quote=False)}" for line in lines]


def _metrics_dict(metrics: EvidenceMetrics) -> dict[str, object]:
    return {
        "total_trials": metrics.total_trials,
        "completed_trials": metrics.completed_trials,
        "passed_trials": metrics.passed_trials,
        "failed_trials": metrics.failed_trials,
        "provider_errors": metrics.provider_errors,
        "pass_rate": metrics.pass_rate,
        "adversarial_trials": metrics.adversarial_trials,
        "false_promotions": metrics.false_promotions,
        "false_promotion_rate": metrics.false_promotion_rate,
        "benign_trials": metrics.benign_trials,
        "false_refusals": metrics.false_refusals,
        "false_refusal_rate": metrics.false_refusal_rate,
        "total_cases": metrics.total_cases,
        "flipped_cases": metrics.flipped_cases,
        "flip_rate": metrics.flip_rate,
    }


def _gate_dict(gate: GateResult) -> dict[str, object]:
    return {
        "name": gate.name,
        "passed": gate.passed,
        "observed": gate.observed,
        "required": gate.required,
        "detail": gate.detail,
    }


def _assessment_dict(assessment: LevelAssessment) -> dict[str, object]:
    return {
        "level": assessment.level.slug,
        "passed": assessment.passed,
        "metrics": _metrics_dict(assessment.metrics),
        "gates": [_gate_dict(gate) for gate in assessment.gates],
    }


def _case_aggregate_dict(item: CaseAggregate, case_by_id: dict[str, object]) -> dict[str, object]:
    case = case_by_id[item.case_id]
    return {
        "id": item.case_id,
        "title": case.title,
        "scenario_type": case.scenario_type,
        "risk_category": case.risk_category,
        "permission_level": case.permission_level,
        "critical": case.critical,
        "tags": list(case.tags),
        "passed_trials": item.passed_trials,
        "failed_trials": item.failed_trials,
        "provider_errors": item.provider_errors,
        "total_trials": item.total_trials,
        "pass_rate": item.pass_rate,
        "flipped": item.flipped,
    }


def _aggregate_normalized_usage(trials: list[TrialResult]) -> dict[str, object]:
    """Sum comparable token counters while preserving raw per-trial usage."""

    totals: dict[str, int] = {}
    trials_with_usage = 0
    for trial in trials:
        usage = trial.result.response.metadata.get("normalized_usage")
        if not isinstance(usage, dict):
            continue
        trials_with_usage += 1
        for key, value in usage.items():
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                totals[key] = totals.get(key, 0) + value
    return {
        "trials_with_normalized_usage": trials_with_usage,
        "totals": dict(sorted(totals.items())),
    }


def write_reports(
    trials: list[TrialResult],
    provider_name: str,
    suite: EvalSuite,
    system_under_test: SystemUnderTest,
    sut_fingerprint: str,
    policy: CalibrationPolicy,
    recommendation: PermissionRecommendation,
    output_dir: Path,
) -> tuple[Path, Path]:
    """Write self-contained JSON and Markdown reports and return their paths."""

    output_dir.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    overall = summarize_trials(trials)
    aggregates = aggregate_trials(trials)
    case_by_id = {case.id: case for case in suite.cases}
    risk_categories = grouped_metrics(trials, lambda trial: trial.result.case.risk_category)
    permission_levels = grouped_metrics(trials, lambda trial: trial.result.case.permission_level)
    repeats = max((trial.trial_index for trial in trials), default=-1) + 1
    normalized_usage = _aggregate_normalized_usage(trials)

    report = {
        "schema_version": "2.0",
        "generated_at": generated_at,
        "suite": {
            "schema_version": suite.schema_version,
            "name": suite.name,
            "description": suite.description,
            "workflow": suite.workflow,
            "version": suite.version,
            "case_count": len(suite.cases),
        },
        "system_under_test": {
            "manifest": system_under_test_dict(system_under_test),
            "fingerprint": sut_fingerprint,
            "fingerprint_algorithm": "sha256 over canonical sorted UTF-8 JSON",
        },
        "execution": {
            "provider": provider_name,
            "repeats": repeats,
            "normalized_usage": normalized_usage,
        },
        "calibration_policy": calibration_policy_dict(policy),
        "summary": {
            **_metrics_dict(overall),
            "risk_categories": {
                name: _metrics_dict(metrics) for name, metrics in risk_categories.items()
            },
            "permission_levels": {
                name: _metrics_dict(metrics) for name, metrics in permission_levels.items()
            },
        },
        "permission_recommendation": {
            "level": recommendation.level.slug,
            "rationale": recommendation.rationale,
            "failed_gates": list(recommendation.failed_gates),
            "assessments": [
                _assessment_dict(assessment) for assessment in recommendation.assessments
            ],
        },
        "case_aggregates": [
            _case_aggregate_dict(item, case_by_id) for item in aggregates
        ],
        "trials": [_trial_dict(trial) for trial in trials],
    }
    json_path = output_dir / "report.json"
    markdown_path = output_dir / "report.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown_path.write_text(
        _markdown_report(
            trials,
            provider_name,
            suite,
            system_under_test,
            sut_fingerprint,
            policy,
            recommendation,
            overall,
            aggregates,
            generated_at,
            normalized_usage,
        ),
        encoding="utf-8",
    )
    return json_path, markdown_path


def _trial_dict(trial: TrialResult) -> dict[str, object]:
    result = trial.result
    return {
        "id": result.case.id,
        "trial_index": trial.trial_index,
        "scenario_type": result.case.scenario_type,
        "risk_category": result.case.risk_category,
        "permission_level": result.case.permission_level,
        "critical": result.case.critical,
        "input": {
            "system_prompt": result.case.system_prompt,
            "prompt": result.case.prompt,
            "context": list(result.case.context),
            "tools": list(result.case.tools),
        },
        "passed": result.passed,
        "response": {
            "text": result.response.text,
            "tool_calls": [
                {"name": call.name, "arguments": call.arguments}
                for call in result.response.tool_calls
            ],
            "provider_metadata": result.response.metadata,
            "error": result.response.error,
        },
        "checks": [
            {"name": check.name, "passed": check.passed, "detail": check.detail}
            for check in result.checks
        ],
    }


def _markdown_report(
    trials: list[TrialResult],
    provider_name: str,
    suite: EvalSuite,
    system: SystemUnderTest,
    fingerprint: str,
    policy: CalibrationPolicy,
    recommendation: PermissionRecommendation,
    overall: EvidenceMetrics,
    aggregates: tuple[CaseAggregate, ...],
    generated_at: str,
    normalized_usage: dict[str, object],
) -> str:
    def rate(value: float | None) -> str:
        return "n/a" if value is None else f"{value:.0%}"

    lines = [
        "# Agent Trust Eval Report",
        "",
        f"- System under test: <code>{escape(system.name)}</code>",
        f"- Fingerprint: <code>{escape(fingerprint)}</code>",
        f"- Workflow: <code>{escape(suite.workflow)}</code>",
        f"- Suite: <code>{escape(suite.name)} {escape(suite.version)}</code>",
        f"- Provider: <code>{escape(provider_name)}</code>",
        f"- Generated: `{generated_at}`",
        f"- Permission recommendation: **{escape(recommendation.level.slug)}**",
        "",
        f"> {escape(recommendation.rationale)} This is policy-relative diagnostic evidence, not a safety certification.",
        "",
        "## Evidence summary",
        "",
        "| Metric | Observed |",
        "|---|---:|",
        f"| Completed trials | {overall.completed_trials}/{overall.total_trials} |",
        f"| Pass rate | {rate(overall.pass_rate)} |",
        f"| False-promotion rate | {rate(overall.false_promotion_rate)} |",
        f"| False-refusal rate | {rate(overall.false_refusal_rate)} |",
        f"| Provider errors | {overall.provider_errors} |",
        f"| Case flip rate | {rate(overall.flip_rate)} |",
        "",
        "## Calibration policy",
        "",
        f"- Minimum pass rate: {policy.minimum_pass_rate:.0%}",
        f"- Maximum false-promotion rate: {policy.maximum_false_promotion_rate:.0%}",
        f"- Maximum false-refusal rate: {policy.maximum_false_refusal_rate:.0%}",
        f"- Maximum flip rate: {policy.maximum_flip_rate:.0%}",
        f"- Maximum v0.1 grant: <code>{escape(policy.maximum_grant.slug)}</code>",
        "",
        "## Permission gates",
        "",
        "| Candidate | Result | Failed gates |",
        "|---|---|---|",
    ]
    usage_totals = normalized_usage["totals"]
    if isinstance(usage_totals, dict) and usage_totals:
        usage_lines = [
            "",
            "## Normalized token usage",
            "",
            f"Usage returned for {normalized_usage['trials_with_normalized_usage']}/{overall.total_trials} trials. Vendor-native usage remains in each raw trial.",
            "",
            "| Token class | Total |",
            "|---|---:|",
        ]
        for key, value in usage_totals.items():
            usage_lines.append(f"| <code>{escape(str(key))}</code> | {value} |")
        calibration_index = lines.index("## Calibration policy")
        lines[calibration_index:calibration_index] = usage_lines
    for assessment in recommendation.assessments:
        failed = ", ".join(gate.name for gate in assessment.gates if not gate.passed) or "none"
        lines.append(
            f"| <code>{escape(assessment.level.slug)}</code> | "
            f"{'PASS' if assessment.passed else 'FAIL'} | {escape(failed)} |"
        )
    lines.extend(
        [
            "",
            "## Case stability",
            "",
            "| Case | Type | Risk | Permission gate | Passed | Errors | Flipped |",
            "|---|---|---|---|---:|---:|---|",
        ]
    )
    case_by_id = {case.id: case for case in suite.cases}
    for item in aggregates:
        case = case_by_id[item.case_id]
        lines.append(
            f"| <code>{escape(item.case_id)}</code> | {escape(case.scenario_type)} | "
            f"{escape(case.risk_category)} | {escape(case.permission_level)} | "
            f"{item.passed_trials}/{item.total_trials} | {item.provider_errors} | "
            f"{'yes' if item.flipped else 'no'} |"
        )
    lines.extend(["", "## Raw trials", ""])
    for trial in trials:
        result = trial.result
        icon = "PASS" if result.passed else "FAIL"
        lines.extend(
            [
                f"### {icon} — {escape(result.case.title)} — trial {trial.trial_index + 1}",
                "",
                f"- ID: <code>{escape(result.case.id)}</code>",
                f"- Type: <code>{escape(result.case.scenario_type)}</code>",
                f"- Risk: <code>{escape(result.case.risk_category)}</code>",
                f"- Permission gate: <code>{escape(result.case.permission_level)}</code>",
                "- Response:",
                "",
                *_code_block(result.response.text or "[No text response]"),
            ]
        )
        if result.response.tool_calls:
            lines.extend(
                [
                    "",
                    "- Tool calls: "
                    + ", ".join(
                        f"<code>{escape(call.name)}</code>" for call in result.response.tool_calls
                    ),
                ]
            )
        if result.response.error:
            lines.extend(["", "- Provider error:", "", *_code_block(result.response.error)])
        if result.response.metadata:
            lines.extend(
                [
                    "",
                    "- Provider metadata:",
                    "",
                    *_code_block(
                        json.dumps(
                            result.response.metadata,
                            ensure_ascii=False,
                            sort_keys=True,
                        )
                    ),
                ]
            )
        lines.extend(["", "| Check | Result | Detail |", "|---|---|---|"])
        for check in result.checks:
            safe_name = escape(check.name).replace("|", "&#124;")
            safe_detail = escape(check.detail).replace("|", "&#124;").replace("\n", " ")
            lines.append(
                f"| <code>{safe_name}</code> | {'PASS' if check.passed else 'FAIL'} | {safe_detail} |"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
