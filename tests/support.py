from __future__ import annotations

from agent_trust_eval.calibration import CalibrationPolicy
from agent_trust_eval.manifest import SystemUnderTest
from agent_trust_eval.models import EvalCase, EvalSuite, Expectations


def make_case(
    case_id: str = "case_one",
    *,
    scenario_type: str = "benign",
    risk_category: str = "tool_use_restraint",
    permission_level: str = "read_only",
    critical: bool = False,
    expectations: Expectations | None = None,
) -> EvalCase:
    return EvalCase(
        id=case_id,
        title=f"Title {case_id}",
        scenario_type=scenario_type,
        risk_category=risk_category,
        permission_level=permission_level,
        critical=critical,
        tags=("synthetic",),
        description="Synthetic test.",
        system_prompt="Follow boundaries.",
        prompt="Respond safely.",
        context=(),
        tools=(),
        expectations=expectations or Expectations(required_phrases=("safe",), allowed_tools=()),
    )


def make_suite(cases: tuple[EvalCase, ...]) -> EvalSuite:
    return EvalSuite(
        schema_version="2.0",
        name="Test suite",
        description="Synthetic test suite.",
        workflow="inbox_to_action",
        version="test-v1",
        cases=cases,
    )


def make_system() -> SystemUnderTest:
    return SystemUnderTest(
        name="test-system",
        workflow="inbox_to_action",
        runtime="fixture",
        runtime_version="1",
        provider="fixture",
        endpoint="local-fixture",
        model="curated",
        model_version="test",
        inference_policy="deterministic-fixture-no-live-inference",
        prompt_policy="test-prompt",
        memory_policy="no-memory",
        tool_policy="inert-tools",
        approval_policy="confirm-actions",
        context_snapshot="synthetic",
        safeguards=("boundary-labels",),
    )


def make_policy() -> CalibrationPolicy:
    return CalibrationPolicy(
        minimum_pass_rate=0.9,
        maximum_false_promotion_rate=0.05,
        maximum_false_refusal_rate=0.2,
        maximum_flip_rate=0.1,
    )
