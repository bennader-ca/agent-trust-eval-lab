from __future__ import annotations

import unittest

from agent_trust_eval.aggregation import TrialResult, aggregate_trials, summarize_trials
from agent_trust_eval.calibration import (
    PermissionLevel,
    calibrate_permission,
    parse_calibration_policy,
)
from agent_trust_eval.grading import grade
from agent_trust_eval.models import EvalCase, ProviderResponse
from tests.support import make_case, make_policy


def trial(case: EvalCase, index: int, *, passed: bool = True, error: str | None = None) -> TrialResult:
    response = ProviderResponse(text="safe" if passed else "wrong", error=error)
    return TrialResult(index, grade(case, response))


def balanced_trials(*, repeats: int = 2) -> list[TrialResult]:
    trials: list[TrialResult] = []
    for permission in (
        "read_only",
        "draft_only",
        "confirm_before_action",
        "reversible_action",
    ):
        for scenario in ("benign", "adversarial"):
            case = make_case(
                f"{permission}_{scenario}",
                permission_level=permission,
                scenario_type=scenario,
                critical=scenario == "adversarial",
            )
            trials.extend(trial(case, index) for index in range(repeats))
    return trials


class AggregationAndCalibrationTests(unittest.TestCase):
    def test_balanced_stable_evidence_earns_reversible_action(self) -> None:
        trials = balanced_trials()
        aggregates = aggregate_trials(trials)
        metrics = summarize_trials(trials)
        recommendation = calibrate_permission(trials, aggregates, make_policy())
        self.assertEqual(metrics.false_promotion_rate, 0.0)
        self.assertEqual(metrics.false_refusal_rate, 0.0)
        self.assertEqual(metrics.flip_rate, 0.0)
        self.assertEqual(recommendation.level, PermissionLevel.REVERSIBLE_ACTION)
        self.assertTrue(all(assessment.passed for assessment in recommendation.assessments))

    def test_critical_failure_caps_at_previous_level(self) -> None:
        trials = balanced_trials()
        target = next(
            item
            for item in trials
            if item.result.case.id == "draft_only_adversarial" and item.trial_index == 0
        )
        trials[trials.index(target)] = trial(target.result.case, 0, passed=False)
        recommendation = calibrate_permission(trials, aggregate_trials(trials), make_policy())
        self.assertEqual(recommendation.level, PermissionLevel.READ_ONLY)
        self.assertIn("draft_only:critical_failures", recommendation.failed_gates)

    def test_flip_and_provider_error_are_visible_and_block_grants(self) -> None:
        benign = make_case("read_benign", permission_level="read_only", scenario_type="benign")
        adversarial = make_case(
            "read_adversarial",
            permission_level="read_only",
            scenario_type="adversarial",
            critical=True,
        )
        flipping = [trial(benign, 0), trial(benign, 1, passed=False)]
        with_error = [trial(adversarial, 0), trial(adversarial, 1, error="timeout")]
        trials = flipping + with_error
        metrics = summarize_trials(trials)
        recommendation = calibrate_permission(trials, aggregate_trials(trials), make_policy())
        self.assertEqual(metrics.provider_errors, 1)
        self.assertEqual(metrics.flipped_cases, 1)
        self.assertEqual(recommendation.level, PermissionLevel.PROHIBITED)
        self.assertIn("read_only:provider_errors", recommendation.failed_gates)

    def test_policy_rejects_consequential_maximum(self) -> None:
        with self.assertRaisesRegex(ValueError, "cannot exceed reversible_action"):
            parse_calibration_policy(
                {
                    "minimum_pass_rate": 0.9,
                    "maximum_false_promotion_rate": 0.05,
                    "maximum_false_refusal_rate": 0.2,
                    "maximum_flip_rate": 0.1,
                    "maximum_grant": "consequential_action",
                }
            )


if __name__ == "__main__":
    unittest.main()
