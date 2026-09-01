from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from agent_trust_eval.cases import load_suite
from agent_trust_eval.cli import main


ROOT = Path(__file__).resolve().parents[1]


class InboxSuiteTests(unittest.TestCase):
    def test_checked_in_sample_matches_safe_profile_contract(self) -> None:
        report = json.loads((ROOT / "sample_output" / "report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["schema_version"], "2.0")
        self.assertEqual(report["suite"]["version"], "0.1.0")
        self.assertEqual(report["suite"]["case_count"], 40)
        self.assertEqual(report["execution"]["repeats"], 3)
        self.assertEqual(report["summary"]["passed_trials"], 120)
        self.assertEqual(report["summary"]["failed_trials"], 0)
        self.assertEqual(report["permission_recommendation"]["level"], "reversible_action")
        self.assertEqual(
            report["system_under_test"]["manifest"]["endpoint"], "local-fixture"
        )

    def test_case_matrix_and_safe_fixture_are_complete(self) -> None:
        suite = load_suite(ROOT / "eval_cases" / "core.json")
        responses = json.loads(
            (ROOT / "fixtures" / "responses" / "inbox-safe.json").read_text(encoding="utf-8")
        )
        self.assertEqual(suite.version, "0.1.0")
        self.assertEqual(len(suite.cases), 40)
        self.assertEqual(set(responses), {case.id for case in suite.cases})
        self.assertEqual(Counter(case.scenario_type for case in suite.cases), {"benign": 20, "adversarial": 20})
        self.assertEqual(
            Counter((case.permission_level, case.scenario_type) for case in suite.cases),
            {
                ("read_only", "benign"): 5,
                ("read_only", "adversarial"): 5,
                ("draft_only", "benign"): 5,
                ("draft_only", "adversarial"): 5,
                ("confirm_before_action", "benign"): 5,
                ("confirm_before_action", "adversarial"): 5,
                ("reversible_action", "benign"): 5,
                ("reversible_action", "adversarial"): 5,
            },
        )
        self.assertTrue(all(case.critical for case in suite.cases if case.scenario_type == "adversarial"))
        positive_tool_cases = [
            case
            for case in suite.cases
            if case.scenario_type == "benign" and case.expectations.required_tools
        ]
        self.assertEqual(len(positive_tool_cases), 10)

    def test_profiles_exercise_expected_permission_paths(self) -> None:
        expectations = {
            "demo.json": ("reversible_action", 0, 0),
            "demo-unsafe.json": ("read_only", 3, 0),
            "demo-unstable.json": ("draft_only", 4, 4),
        }
        with tempfile.TemporaryDirectory() as directory:
            for name, (level, failures, flips) in expectations.items():
                output = Path(directory) / name
                with contextlib.redirect_stdout(io.StringIO()):
                    status = main(
                        [
                            "--config",
                            str(ROOT / "configs" / name),
                            "--output",
                            str(output),
                        ]
                    )
                self.assertEqual(status, 0, name)
                report = json.loads((output / "report.json").read_text(encoding="utf-8"))
                self.assertEqual(report["suite"]["case_count"], 40, name)
                self.assertEqual(report["execution"]["repeats"], 3, name)
                self.assertEqual(len(report["trials"]), 120, name)
                self.assertEqual(report["permission_recommendation"]["level"], level, name)
                self.assertEqual(report["summary"]["failed_trials"], failures, name)
                self.assertEqual(report["summary"]["flipped_cases"], flips, name)


if __name__ == "__main__":
    unittest.main()
