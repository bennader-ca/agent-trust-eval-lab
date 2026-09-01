from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from agent_trust_eval.cli import main


ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def test_demo_run_writes_both_reports_and_returns_zero(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "reports"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                status = main(
                    [
                        "--config",
                        str(ROOT / "configs" / "demo.json"),
                        "--output",
                        str(output),
                        "--fail-on-case-failure",
                    ]
                )
            self.assertEqual(status, 0)
            self.assertTrue((output / "report.json").is_file())
            self.assertTrue((output / "report.md").is_file())
            self.assertIn("120 passed, 0 failed or errored", stdout.getvalue())
            report = json.loads((output / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["schema_version"], "2.0")
            self.assertIn("Permission recommendation:", stdout.getvalue())

    def test_strict_mode_returns_one_for_completed_failing_run(self) -> None:
        demo = json.loads((ROOT / "configs" / "demo.json").read_text(encoding="utf-8"))
        demo["suite"] = str(ROOT / "eval_cases" / "core.json")
        demo["provider"]["responses_file"] = str(
            ROOT / "fixtures" / "responses" / "inbox-safe.json"
        )
        demo["provider"]["overrides"] = {
            "read_summary_injection": {"text": "BLUEBIRD", "tool_calls": []}
        }
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "failing.json"
            config.write_text(json.dumps(demo), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                status = main(
                    [
                        "--config",
                        str(config),
                        "--output",
                        str(Path(directory) / "reports"),
                        "--fail-on-case-failure",
                    ]
                )
        self.assertEqual(status, 1)

    def test_repeats_override_preserves_config_and_changes_execution(self) -> None:
        config = ROOT / "configs" / "demo.json"
        original = config.read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report"
            with contextlib.redirect_stdout(io.StringIO()):
                status = main(
                    [
                        "--config",
                        str(config),
                        "--repeats",
                        "1",
                        "--output",
                        str(output),
                    ]
                )
            report = json.loads((output / "report.json").read_text(encoding="utf-8"))
        self.assertEqual(status, 0)
        self.assertEqual(report["execution"]["repeats"], 1)
        self.assertEqual(report["summary"]["total_trials"], 40)
        self.assertEqual(config.read_bytes(), original)

    def test_repeats_override_rejects_out_of_range_value(self) -> None:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            status = main(
                [
                    "--config",
                    str(ROOT / "configs" / "demo.json"),
                    "--repeats",
                    "0",
                    "--validate-only",
                ]
            )
        self.assertEqual(status, 2)
        self.assertIn("--repeats must be an integer from 1 through 100", stderr.getvalue())

    def test_study_configs_validate_and_ablation_changes_only_disclosed_fields(self) -> None:
        study_names = (
            "study-openai-terra.json",
            "study-anthropic-sonnet.json",
            "study-google-gemini.json",
            "study-openai-terra-unlabeled-context.json",
        )
        for name in study_names:
            with self.subTest(name=name), contextlib.redirect_stdout(io.StringIO()):
                status = main(
                    [
                        "--config",
                        str(ROOT / "configs" / name),
                        "--validate-only",
                    ]
                )
            self.assertEqual(status, 0)

        baseline = json.loads(
            (ROOT / "configs" / "study-openai-terra.json").read_text(encoding="utf-8")
        )
        ablation = json.loads(
            (
                ROOT / "configs" / "study-openai-terra-unlabeled-context.json"
            ).read_text(encoding="utf-8")
        )
        baseline_system = dict(baseline["system_under_test"])
        ablation_system = dict(ablation["system_under_test"])
        for field in ("name", "runtime_version", "safeguards"):
            baseline_system.pop(field)
            ablation_system.pop(field)
        self.assertEqual(baseline_system, ablation_system)
        baseline_provider = dict(baseline["provider"])
        ablation_provider = dict(ablation["provider"])
        baseline_provider.pop("context_mode")
        ablation_provider.pop("context_mode")
        self.assertEqual(baseline_provider, ablation_provider)
        self.assertEqual(baseline["schema_version"], ablation["schema_version"])
        self.assertEqual(baseline["suite"], ablation["suite"])
        self.assertEqual(baseline["repeats"], ablation["repeats"])
        self.assertEqual(baseline["calibration_policy"], ablation["calibration_policy"])
        self.assertIn("untrusted-context-labeling", baseline["system_under_test"]["safeguards"])
        self.assertNotIn("untrusted-context-labeling", ablation["system_under_test"]["safeguards"])
        self.assertEqual(baseline["provider"]["context_mode"], "labeled_untrusted")
        self.assertEqual(ablation["provider"]["context_mode"], "unlabeled_context")

    def test_malformed_config_returns_two_with_clear_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "bad.json"
            config.write_text("not-json", encoding="utf-8")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                status = main(["--config", str(config)])
        self.assertEqual(status, 2)
        self.assertIn("invalid JSON", stderr.getvalue())

    def test_unknown_provider_returns_two(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "unknown.json"
            value = json.loads((ROOT / "configs" / "demo.json").read_text(encoding="utf-8"))
            value["suite"] = str(ROOT / "eval_cases" / "core.json")
            value["provider"] = {"type": "unknown"}
            config.write_text(json.dumps(value), encoding="utf-8")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                status = main(["--config", str(config)])
        self.assertEqual(status, 2)
        self.assertIn("unknown provider type", stderr.getvalue())

    def test_live_provider_model_must_match_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            value = json.loads(
                (ROOT / "configs" / "openai-responses.example.json").read_text(
                    encoding="utf-8"
                )
            )
            value["suite"] = str(ROOT / "eval_cases" / "core.json")
            value["system_under_test"]["model"] = "manifest-model"
            value["system_under_test"]["model_version"] = "synthetic-snapshot"
            value["provider"]["model"] = "different-provider-model"
            config = Path(directory) / "mismatch.json"
            config.write_text(json.dumps(value), encoding="utf-8")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                status = main(["--config", str(config)])
        self.assertEqual(status, 2)
        self.assertIn("provider.model must match", stderr.getvalue())

    def test_live_context_mode_must_match_manifest_safeguards(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            value = json.loads(
                (ROOT / "configs" / "openai-responses.example.json").read_text(
                    encoding="utf-8"
                )
            )
            value["suite"] = str(ROOT / "eval_cases" / "core.json")
            value["system_under_test"]["model"] = "synthetic-pinned-model"
            value["system_under_test"]["model_version"] = "synthetic-snapshot"
            value["provider"]["model"] = "synthetic-pinned-model"
            value["provider"]["context_mode"] = "unlabeled_context"
            config = Path(directory) / "context-mismatch.json"
            config.write_text(json.dumps(value), encoding="utf-8")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                status = main(["--config", str(config)])
        self.assertEqual(status, 2)
        self.assertIn("context_mode must agree", stderr.getvalue())

    def test_native_examples_validate_without_api_keys_or_calls(self) -> None:
        examples = (
            "openai-responses.example.json",
            "anthropic-messages.example.json",
            "gemini-generate-content.example.json",
        )
        for example in examples:
            with self.subTest(example=example):
                value = json.loads(
                    (ROOT / "configs" / example).read_text(encoding="utf-8")
                )
                value["suite"] = str(ROOT / "eval_cases" / "core.json")
                value["system_under_test"]["model"] = "synthetic-pinned-model"
                value["system_under_test"]["model_version"] = "synthetic-snapshot"
                value["provider"]["model"] = "synthetic-pinned-model"
                if value["provider"]["type"] == "gemini_generate_content":
                    value["system_under_test"]["endpoint"] = (
                        "https://generativelanguage.googleapis.com/v1beta/models/"
                        "synthetic-pinned-model:generateContent"
                    )
                with tempfile.TemporaryDirectory() as directory:
                    config = Path(directory) / example
                    config.write_text(json.dumps(value), encoding="utf-8")
                    stdout = io.StringIO()
                    with contextlib.redirect_stdout(stdout):
                        status = main(
                            [
                                "--config",
                                str(config),
                                "--validate-only",
                            ]
                        )
                self.assertEqual(status, 0)
                self.assertIn("Valid configuration for 40 cases x 5 repeats", stdout.getvalue())
                self.assertIn("SUT fingerprint:", stdout.getvalue())

    def test_validate_only_rejects_unedited_example_placeholders(self) -> None:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            status = main(
                [
                    "--config",
                    str(ROOT / "configs" / "openai-responses.example.json"),
                    "--validate-only",
                ]
            )
        self.assertEqual(status, 2)
        self.assertIn("example placeholder", stderr.getvalue())

    def test_live_endpoint_must_match_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            value = json.loads(
                (ROOT / "configs" / "openai-responses.example.json").read_text(
                    encoding="utf-8"
                )
            )
            value["suite"] = str(ROOT / "eval_cases" / "core.json")
            value["system_under_test"]["model"] = "synthetic-pinned-model"
            value["system_under_test"]["model_version"] = "synthetic-snapshot"
            value["system_under_test"]["endpoint"] = "https://proxy.invalid/v1/responses"
            value["provider"]["model"] = "synthetic-pinned-model"
            config = Path(directory) / "endpoint-mismatch.json"
            config.write_text(json.dumps(value), encoding="utf-8")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                status = main(["--config", str(config), "--validate-only"])
        self.assertEqual(status, 2)
        self.assertIn("endpoint must match", stderr.getvalue())

    def test_live_inference_policy_must_match_provider_settings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            value = json.loads(
                (ROOT / "configs" / "openai-responses.example.json").read_text(
                    encoding="utf-8"
                )
            )
            value["suite"] = str(ROOT / "eval_cases" / "core.json")
            value["system_under_test"]["model"] = "synthetic-pinned-model"
            value["system_under_test"]["model_version"] = "synthetic-snapshot"
            value["provider"]["model"] = "synthetic-pinned-model"
            value["provider"]["reasoning_effort"] = "low"
            config = Path(directory) / "inference-mismatch.json"
            config.write_text(json.dumps(value), encoding="utf-8")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                status = main(["--config", str(config), "--validate-only"])
        self.assertEqual(status, 2)
        self.assertIn("inference_policy must match", stderr.getvalue())

    def test_native_configs_run_end_to_end_against_mocked_contracts(self) -> None:
        contracts = {
            "openai-responses.example.json": {
                "env": "OPENAI_API_KEY",
                "response": {
                    "output": [
                        {
                            "type": "message",
                            "content": [{"type": "output_text", "text": "safe"}],
                        }
                    ]
                },
            },
            "anthropic-messages.example.json": {
                "env": "ANTHROPIC_API_KEY",
                "response": {"content": [{"type": "text", "text": "safe"}]},
            },
            "gemini-generate-content.example.json": {
                "env": "GEMINI_API_KEY",
                "response": {
                    "candidates": [
                        {"content": {"parts": [{"text": "safe"}]}}
                    ]
                },
            },
        }
        for example, contract in contracts.items():
            with self.subTest(example=example), tempfile.TemporaryDirectory() as directory:
                value = json.loads(
                    (ROOT / "configs" / example).read_text(encoding="utf-8")
                )
                value["suite"] = str(ROOT / "eval_cases" / "core.json")
                value["repeats"] = 1
                value["system_under_test"]["model"] = "synthetic-pinned-model"
                value["system_under_test"]["model_version"] = "synthetic-snapshot"
                value["provider"]["model"] = "synthetic-pinned-model"
                if value["provider"]["type"] == "gemini_generate_content":
                    value["system_under_test"]["endpoint"] = (
                        "https://generativelanguage.googleapis.com/v1beta/models/"
                        "synthetic-pinned-model:generateContent"
                    )
                config = Path(directory) / example
                config.write_text(json.dumps(value), encoding="utf-8")
                response = MagicMock()
                response.__enter__.return_value = response
                response.read.return_value = json.dumps(contract["response"]).encode()
                output = Path(directory) / "report"
                with patch.dict(
                    os.environ, {str(contract["env"]): "test-only-key"}, clear=False
                ):
                    with patch(
                        "agent_trust_eval.providers.urlopen", return_value=response
                    ) as opened:
                        with contextlib.redirect_stdout(io.StringIO()):
                            status = main(
                                [
                                    "--config",
                                    str(config),
                                    "--output",
                                    str(output),
                                ]
                            )
                report = json.loads((output / "report.json").read_text(encoding="utf-8"))
                self.assertEqual(status, 0)
                self.assertEqual(opened.call_count, 40)
                self.assertEqual(report["summary"]["total_trials"], 40)
                self.assertEqual(report["summary"]["provider_errors"], 0)


if __name__ == "__main__":
    unittest.main()
