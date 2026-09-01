from __future__ import annotations

import copy
from collections import Counter
import json
import tempfile
import unittest
from pathlib import Path

from agent_trust_eval.cases import CaseValidationError, load_cases


ROOT = Path(__file__).resolve().parents[1]


def minimal_suite() -> dict[str, object]:
    return {
        "schema_version": "2.0",
        "name": "test suite",
        "description": "synthetic test suite",
        "workflow": "inbox_to_action",
        "version": "test-v1",
        "cases": [
            {
                "id": "case_one",
                "title": "Case one",
                "scenario_type": "benign",
                "risk_category": "prompt_injection",
                "permission_level": "read_only",
                "critical": False,
                "tags": ["synthetic"],
                "description": "A synthetic case.",
                "system_prompt": "Follow trusted instructions.",
                "prompt": "Summarize the data.",
                "context": [],
                "tools": [],
                "expectations": {"required_phrases": ["summary"], "allowed_tools": []},
            }
        ],
    }


class CaseLoadingTests(unittest.TestCase):
    def write_suite(self, value: object) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "suite.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_real_suite_has_expected_shape_and_order(self) -> None:
        cases = load_cases(ROOT / "eval_cases" / "core.json")
        self.assertEqual(len(cases), 40)
        self.assertEqual(Counter(case.scenario_type for case in cases), {"benign": 20, "adversarial": 20})
        self.assertEqual(
            Counter((case.permission_level, case.scenario_type) for case in cases),
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
        self.assertTrue(all(case.critical for case in cases if case.scenario_type == "adversarial"))
        self.assertGreaterEqual(len({case.risk_category for case in cases}), 8)
        self.assertEqual(len({case.id for case in cases}), len(cases))

    def test_rejects_invalid_json(self) -> None:
        path = self.write_suite({})
        path.write_text("not json", encoding="utf-8")
        with self.assertRaisesRegex(CaseValidationError, "invalid JSON"):
            load_cases(path)

    def test_rejects_unknown_category(self) -> None:
        suite = minimal_suite()
        suite["cases"][0]["risk_category"] = "made_up"  # type: ignore[index]
        with self.assertRaisesRegex(CaseValidationError, "must be one of"):
            load_cases(self.write_suite(suite))

    def test_rejects_duplicate_ids(self) -> None:
        suite = minimal_suite()
        suite["cases"].append(copy.deepcopy(suite["cases"][0]))  # type: ignore[union-attr,index]
        with self.assertRaisesRegex(CaseValidationError, "duplicated"):
            load_cases(self.write_suite(suite))

    def test_rejects_empty_expectations(self) -> None:
        suite = minimal_suite()
        suite["cases"][0]["expectations"] = {}  # type: ignore[index]
        with self.assertRaisesRegex(CaseValidationError, "at least one grading rule"):
            load_cases(self.write_suite(suite))

    def test_rejects_undeclared_allowed_tool(self) -> None:
        suite = minimal_suite()
        suite["cases"][0]["expectations"] = {"allowed_tools": ["send_message"]}  # type: ignore[index]
        with self.assertRaisesRegex(CaseValidationError, "undeclared tools"):
            load_cases(self.write_suite(suite))


if __name__ == "__main__":
    unittest.main()
