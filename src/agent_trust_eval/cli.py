"""Command-line entry point."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .aggregation import aggregate_trials
from .calibration import (
    CalibrationPolicy,
    CalibrationPolicyError,
    calibrate_permission,
    parse_calibration_policy,
)
from .cases import CaseValidationError, load_suite
from .manifest import (
    ManifestValidationError,
    SystemUnderTest,
    fingerprint_system_under_test,
    parse_system_under_test,
)
from .providers import (
    ProviderConfigError,
    build_provider,
    provider_endpoint,
    provider_inference_policy,
)
from .reporting import write_reports
from .runner import run_cases


class ConfigError(ValueError):
    """Raised for an invalid run configuration."""


def _load_config(
    path: Path,
) -> tuple[Path, int, SystemUnderTest, CalibrationPolicy, dict[str, object]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"config file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"invalid JSON in {path}: line {exc.lineno}, column {exc.colno}") from exc
    if not isinstance(raw, dict):
        raise ConfigError(f"{path} must contain a JSON object")
    required = {
        "schema_version",
        "suite",
        "repeats",
        "system_under_test",
        "calibration_policy",
        "provider",
    }
    missing = sorted(required - raw.keys())
    unknown = sorted(raw.keys() - required)
    if missing:
        raise ConfigError(f"config is missing required keys: {', '.join(missing)}")
    if unknown:
        raise ConfigError(f"config has unknown keys: {', '.join(unknown)}")
    if raw["schema_version"] != "2.0":
        raise ConfigError("config.schema_version must be '2.0'; v1 configs require migration")
    if not isinstance(raw["suite"], str) or not raw["suite"].strip():
        raise ConfigError("config.suite must be a non-empty path string")
    if not isinstance(raw["provider"], dict):
        raise ConfigError("config.provider must be an object")
    repeats = raw["repeats"]
    if not isinstance(repeats, int) or isinstance(repeats, bool) or not 1 <= repeats <= 100:
        raise ConfigError("config.repeats must be an integer from 1 through 100")
    system = parse_system_under_test(raw["system_under_test"])
    policy = parse_calibration_policy(raw["calibration_policy"])
    provider = _resolve_provider_files(raw["provider"], path.parent)
    return (path.parent / raw["suite"]).resolve(), repeats, system, policy, provider


def _resolve_provider_files(
    provider: dict[str, object], config_dir: Path
) -> dict[str, object]:
    """Resolve optional local fixture response files and explicit overrides."""

    if provider.get("type") != "fixture" or "responses_file" not in provider:
        if "overrides" in provider:
            raise ConfigError("provider.overrides requires provider.responses_file")
        return provider
    if "responses" in provider:
        raise ConfigError("fixture provider must use either responses or responses_file, not both")
    allowed = {"type", "name", "responses_file", "overrides"}
    unknown = sorted(provider.keys() - allowed)
    if unknown:
        raise ConfigError(f"provider has unknown keys: {', '.join(unknown)}")
    raw_path = provider["responses_file"]
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ConfigError("provider.responses_file must be a non-empty path string")
    response_path = (config_dir / raw_path).resolve()
    try:
        responses = json.loads(response_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"fixture response file not found: {response_path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(
            f"invalid JSON in {response_path}: line {exc.lineno}, column {exc.colno}"
        ) from exc
    if not isinstance(responses, dict) or not responses:
        raise ConfigError("provider.responses_file must contain a non-empty JSON object")
    overrides = provider.get("overrides", {})
    if not isinstance(overrides, dict):
        raise ConfigError("provider.overrides must be a JSON object")
    return {
        "type": "fixture",
        "name": provider.get("name", "fixture"),
        "responses": {**responses, **overrides},
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-trust-eval",
        description="Calibrate bounded agent permissions from transparent repeated workflow probes.",
    )
    parser.add_argument("--config", type=Path, default=Path("configs/demo.json"), help="run configuration JSON")
    parser.add_argument("--output", type=Path, default=Path("reports/latest"), help="report output directory")
    parser.add_argument(
        "--repeats",
        type=int,
        help="override config repeats for this execution without changing the config file",
    )
    parser.add_argument(
        "--fail-on-case-failure",
        action="store_true",
        help="return exit status 1 when any case fails; completed evaluations otherwise return 0",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="validate config, suite, SUT binding, and provider without calling an endpoint",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the Agent Trust Eval Lab CLI."""

    args = _parser().parse_args(argv)
    try:
        suite_path, repeats, system, policy, provider_config = _load_config(args.config.resolve())
        if args.repeats is not None:
            if not 1 <= args.repeats <= 100:
                raise ConfigError("--repeats must be an integer from 1 through 100")
            repeats = args.repeats
        suite = load_suite(suite_path)
        if suite.workflow != system.workflow:
            raise ConfigError(
                "config.system_under_test.workflow must match the configured suite workflow"
            )
        configured_model = provider_config.get("model")
        if configured_model is not None and configured_model != system.model:
            raise ConfigError(
                "config.provider.model must match config.system_under_test.model"
            )
        context_mode = provider_config.get("context_mode")
        if context_mode is not None:
            declares_labeling = "untrusted-context-labeling" in system.safeguards
            applies_labeling = context_mode == "labeled_untrusted"
            if declares_labeling != applies_labeling:
                raise ConfigError(
                    "config.provider.context_mode must agree with the "
                    "untrusted-context-labeling SUT safeguard"
                )
        provider = build_provider(provider_config)
        resolved_endpoint = provider_endpoint(provider_config)
        if resolved_endpoint != system.endpoint:
            raise ConfigError(
                "config.system_under_test.endpoint must match the resolved provider endpoint"
            )
        resolved_inference_policy = provider_inference_policy(provider_config)
        if resolved_inference_policy != system.inference_policy:
            raise ConfigError(
                "config.system_under_test.inference_policy must match the resolved "
                "provider inference policy"
            )
        fingerprint = fingerprint_system_under_test(system)
        if args.validate_only:
            print(
                f"Valid configuration for {len(suite.cases)} cases x {repeats} repeats "
                f"with {provider.name}"
            )
            print(f"SUT fingerprint: {fingerprint}")
            return 0
        trials = run_cases(list(suite.cases), provider, repeats)
        aggregates = aggregate_trials(trials)
        recommendation = calibrate_permission(trials, aggregates, policy)
        json_path, markdown_path = write_reports(
            trials,
            provider.name,
            suite,
            system,
            fingerprint,
            policy,
            recommendation,
            args.output.resolve(),
        )
    except (
        CalibrationPolicyError,
        CaseValidationError,
        ConfigError,
        ManifestValidationError,
        ProviderConfigError,
        OSError,
        ValueError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    passed = sum(trial.result.passed for trial in trials)
    print(
        f"Completed {len(suite.cases)} cases x {repeats} repeats with {provider.name}: "
        f"{passed} passed, {len(trials) - passed} failed or errored"
    )
    print(f"SUT fingerprint: {fingerprint}")
    print(f"Permission recommendation: {recommendation.level.slug}")
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {markdown_path}")
    if args.fail_on_case_failure and passed != len(trials):
        return 1
    return 0
