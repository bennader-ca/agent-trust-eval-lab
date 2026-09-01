"""Repeated-trial aggregation for authority-calibration evidence."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Callable

from .models import CaseResult


@dataclass(frozen=True)
class TrialResult:
    """One graded case execution within a repeated run."""

    trial_index: int
    result: CaseResult


@dataclass(frozen=True)
class CaseAggregate:
    """Stability and error evidence for one case across trials."""

    case_id: str
    passed_trials: int
    failed_trials: int
    provider_errors: int
    total_trials: int
    pass_rate: float | None
    flipped: bool


@dataclass(frozen=True)
class EvidenceMetrics:
    """Transparent safety, utility, stability, and availability metrics."""

    total_trials: int
    completed_trials: int
    passed_trials: int
    failed_trials: int
    provider_errors: int
    pass_rate: float | None
    adversarial_trials: int
    false_promotions: int
    false_promotion_rate: float | None
    benign_trials: int
    false_refusals: int
    false_refusal_rate: float | None
    total_cases: int
    flipped_cases: int
    flip_rate: float | None


def aggregate_trials(trials: list[TrialResult]) -> tuple[CaseAggregate, ...]:
    """Aggregate raw trial results without discarding them."""

    grouped: dict[str, list[TrialResult]] = defaultdict(list)
    order: list[str] = []
    for trial in trials:
        case_id = trial.result.case.id
        if case_id not in grouped:
            order.append(case_id)
        grouped[case_id].append(trial)

    aggregates: list[CaseAggregate] = []
    for case_id in order:
        case_trials = grouped[case_id]
        completed = [trial for trial in case_trials if trial.result.response.error is None]
        passed = sum(trial.result.passed for trial in completed)
        failed = len(completed) - passed
        outcomes = {trial.result.passed for trial in completed}
        aggregates.append(
            CaseAggregate(
                case_id=case_id,
                passed_trials=passed,
                failed_trials=failed,
                provider_errors=len(case_trials) - len(completed),
                total_trials=len(case_trials),
                pass_rate=_rate(passed, len(completed)),
                flipped=len(outcomes) > 1,
            )
        )
    return tuple(aggregates)


def summarize_trials(trials: list[TrialResult]) -> EvidenceMetrics:
    """Compute aggregate metrics with explicit error-aware denominators."""

    completed = [trial for trial in trials if trial.result.response.error is None]
    passed = sum(trial.result.passed for trial in completed)
    adversarial = [trial for trial in completed if trial.result.case.scenario_type == "adversarial"]
    benign = [trial for trial in completed if trial.result.case.scenario_type == "benign"]
    false_promotions = sum(not trial.result.passed for trial in adversarial)
    false_refusals = sum(not trial.result.passed for trial in benign)
    case_aggregates = aggregate_trials(trials)
    flipped = sum(item.flipped for item in case_aggregates)
    return EvidenceMetrics(
        total_trials=len(trials),
        completed_trials=len(completed),
        passed_trials=passed,
        failed_trials=len(completed) - passed,
        provider_errors=len(trials) - len(completed),
        pass_rate=_rate(passed, len(completed)),
        adversarial_trials=len(adversarial),
        false_promotions=false_promotions,
        false_promotion_rate=_rate(false_promotions, len(adversarial)),
        benign_trials=len(benign),
        false_refusals=false_refusals,
        false_refusal_rate=_rate(false_refusals, len(benign)),
        total_cases=len(case_aggregates),
        flipped_cases=flipped,
        flip_rate=_rate(flipped, len(case_aggregates)),
    )


def grouped_metrics(
    trials: list[TrialResult], key: Callable[[TrialResult], str]
) -> dict[str, EvidenceMetrics]:
    """Summarize trials by a stable string key in first-seen order."""

    grouped: dict[str, list[TrialResult]] = defaultdict(list)
    for trial in trials:
        grouped[key(trial)].append(trial)
    return {name: summarize_trials(items) for name, items in grouped.items()}


def _rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None
