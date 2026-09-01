from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from agent_trust_eval.cli import main as eval_main
from agent_trust_eval.comparison import main as compare_main


ROOT = Path(__file__).resolve().parents[1]


class ComparisonTests(unittest.TestCase):
    def _generate_reports(self, directory: Path) -> list[Path]:
        reports: list[Path] = []
        for config_name in ("demo.json", "demo-unsafe.json", "demo-unstable.json"):
            output = directory / config_name.removesuffix(".json")
            with contextlib.redirect_stdout(io.StringIO()):
                status = eval_main(
                    [
                        "--config",
                        str(ROOT / "configs" / config_name),
                        "--output",
                        str(output),
                    ]
                )
            self.assertEqual(status, 0)
            reports.append(output / "report.json")
        return reports

    def test_compare_writes_whitelisted_json_and_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            reports = self._generate_reports(directory)
            first = json.loads(reports[0].read_text(encoding="utf-8"))
            first["execution"]["normalized_usage"] = {
                "totals": {"input_tokens": 1200, "output_tokens": 300}
            }
            reports[0].write_text(json.dumps(first), encoding="utf-8")
            output = directory / "comparison"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                status = compare_main(
                    [*(str(report) for report in reports), "--output", str(output)]
                )
            comparison = json.loads(
                (output / "comparison.json").read_text(encoding="utf-8")
            )
            markdown = (output / "comparison.md").read_text(encoding="utf-8")

        self.assertEqual(status, 0)
        self.assertEqual(comparison["schema_version"], "1.0")
        self.assertEqual(comparison["run_count"], 3)
        self.assertEqual(
            [run["permission_recommendation"] for run in comparison["runs"]],
            ["reversible_action", "read_only", "draft_only"],
        )
        self.assertNotIn("trials", comparison["runs"][0])
        self.assertEqual(comparison["runs"][0]["normalized_usage"]["input_tokens"], 1200)
        self.assertIn("<code>input_tokens</code>", markdown)
        self.assertIn("| 1 | 1200 | 300 |", markdown)
        self.assertIn("Source report SHA-256", markdown)
        self.assertIn("does not name an overall winner", markdown)
        self.assertIn("Compared 3 compatible reports", stdout.getvalue())

    def test_compare_rejects_different_policy(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            reports = self._generate_reports(directory)
            changed = json.loads(reports[1].read_text(encoding="utf-8"))
            changed["calibration_policy"]["minimum_pass_rate"] = 0.8
            reports[1].write_text(json.dumps(changed), encoding="utf-8")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                status = compare_main([*(str(report) for report in reports)])
        self.assertEqual(status, 2)
        self.assertIn("suite and calibration policy", stderr.getvalue())

    def test_compare_rejects_duplicate_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            reports = self._generate_reports(Path(directory_name))
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                status = compare_main([str(reports[0]), str(reports[0])])
        self.assertEqual(status, 2)
        self.assertIn("same report more than once", stderr.getvalue())

    def test_compare_rejects_changed_case_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory_name:
            directory = Path(directory_name)
            reports = self._generate_reports(directory)
            changed = json.loads(reports[1].read_text(encoding="utf-8"))
            changed["case_aggregates"][0]["id"] = "substituted-case"
            reports[1].write_text(json.dumps(changed), encoding="utf-8")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                status = compare_main([*(str(report) for report in reports)])
        self.assertEqual(status, 2)
        self.assertIn("suite and calibration policy", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
