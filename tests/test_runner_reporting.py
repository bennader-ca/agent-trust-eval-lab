from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agent_trust_eval.aggregation import aggregate_trials
from agent_trust_eval.calibration import calibrate_permission
from agent_trust_eval.manifest import fingerprint_system_under_test
from agent_trust_eval.models import EvalCase, ProviderResponse
from agent_trust_eval.reporting import write_reports
from agent_trust_eval.runner import run_cases
from tests.support import make_case, make_policy, make_suite, make_system


class SequenceProvider:
    name = "sequence-provider"

    def complete(self, case: EvalCase, trial_index: int = 0) -> ProviderResponse:
        if case.id == "second":
            raise RuntimeError("synthetic timeout")
        return ProviderResponse(text="safe response")


class RunnerAndReportingTests(unittest.TestCase):
    def test_runner_preserves_order_and_captures_provider_failure(self) -> None:
        cases = [make_case("first"), make_case("second"), make_case("third")]
        results = run_cases(cases, SequenceProvider())
        self.assertEqual([trial.result.case.id for trial in results], ["first", "second", "third"])
        self.assertTrue(results[0].result.passed)
        self.assertFalse(results[1].result.passed)
        self.assertIn("synthetic timeout", results[1].result.response.error or "")
        self.assertTrue(results[2].result.passed)

    def test_reports_are_structured_and_escape_active_model_markup(self) -> None:
        class MarkupProvider:
            name = "markup-provider"

            def complete(self, case: EvalCase, trial_index: int = 0) -> ProviderResponse:
                return ProviderResponse(
                    text="safe\n<script>alert('x')</script>",
                    metadata={
                        "resolved_model": "synthetic-model",
                        "usage": {"total": 2},
                        "normalized_usage": {
                            "input_tokens": 1,
                            "output_tokens": 1,
                            "total_tokens": 2,
                        },
                    },
                )

        cases = [make_case("markup", risk_category="provenance")]
        suite = make_suite(tuple(cases))
        system = make_system()
        policy = make_policy()
        results = run_cases(cases, MarkupProvider(), repeats=2)
        aggregates = aggregate_trials(results)
        recommendation = calibrate_permission(results, aggregates, policy)
        with tempfile.TemporaryDirectory() as directory:
            json_path, markdown_path = write_reports(
                results,
                "markup-provider",
                suite,
                system,
                fingerprint_system_under_test(system),
                policy,
                recommendation,
                Path(directory),
            )
            report = json.loads(json_path.read_text(encoding="utf-8"))
            markdown = markdown_path.read_text(encoding="utf-8")
        self.assertEqual(report["schema_version"], "2.0")
        self.assertEqual(report["summary"]["total_trials"], 2)
        self.assertEqual(
            report["execution"]["normalized_usage"]["totals"]["total_tokens"], 4
        )
        self.assertEqual(report["summary"]["risk_categories"]["provenance"]["passed_trials"], 2)
        self.assertIn("fingerprint", report["system_under_test"])
        self.assertIn("permission_recommendation", report)
        self.assertEqual(len(report["trials"]), 2)
        self.assertEqual(
            report["trials"][0]["response"]["provider_metadata"]["resolved_model"],
            "synthetic-model",
        )
        self.assertNotIn("<script>", markdown)
        self.assertIn("&lt;script&gt;", markdown)
        self.assertIn("synthetic-model", markdown)
        self.assertIn("Normalized token usage", markdown)
        self.assertIn("    safe", markdown)


if __name__ == "__main__":
    unittest.main()
