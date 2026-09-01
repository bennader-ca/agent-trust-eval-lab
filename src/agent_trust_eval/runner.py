"""Evaluation suite orchestration."""

from __future__ import annotations

from .grading import grade
from .aggregation import TrialResult
from .models import EvalCase, ProviderResponse
from .providers import Provider


def run_cases(cases: list[EvalCase], provider: Provider, repeats: int = 1) -> list[TrialResult]:
    """Execute each case *repeats* times in deterministic case-major order."""

    if not isinstance(repeats, int) or isinstance(repeats, bool) or not 1 <= repeats <= 100:
        raise ValueError("repeats must be an integer from 1 through 100")
    results: list[TrialResult] = []
    for case in cases:
        for trial_index in range(repeats):
            try:
                response = provider.complete(case, trial_index)
            except Exception as exc:  # Provider boundaries must not abort the suite.
                response = ProviderResponse(text="", error=f"{type(exc).__name__}: {exc}")
            results.append(TrialResult(trial_index=trial_index, result=grade(case, response)))
    return results
