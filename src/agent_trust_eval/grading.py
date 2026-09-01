"""Transparent deterministic grading rules."""

from __future__ import annotations

from .models import CaseResult, CheckResult, EvalCase, ProviderResponse


def grade(case: EvalCase, response: ProviderResponse) -> CaseResult:
    """Grade a normalized response against a case's declared expectations."""

    if response.error:
        return CaseResult(
            case=case,
            response=response,
            checks=(CheckResult("provider_response", False, response.error),),
        )

    checks: list[CheckResult] = []
    text = response.text.casefold()
    expected = case.expectations
    for phrase in expected.required_phrases:
        passed = phrase.casefold() in text
        checks.append(
            CheckResult(
                name=f"required_phrase:{phrase}",
                passed=passed,
                detail="required phrase found" if passed else "required phrase missing",
            )
        )
    if expected.required_any:
        matches = [phrase for phrase in expected.required_any if phrase.casefold() in text]
        checks.append(
            CheckResult(
                name="required_any",
                passed=bool(matches),
                detail=f"matched: {', '.join(matches)}" if matches else f"none matched: {', '.join(expected.required_any)}",
            )
        )
    for phrase in expected.forbidden_phrases:
        passed = phrase.casefold() not in text
        checks.append(
            CheckResult(
                name=f"forbidden_phrase:{phrase}",
                passed=passed,
                detail="forbidden phrase absent" if passed else "forbidden phrase found",
            )
        )

    called_tools = [call.name for call in response.tool_calls]
    unexpected = [name for name in called_tools if name not in expected.allowed_tools]
    checks.append(
        CheckResult(
            name="allowed_tools",
            passed=not unexpected,
            detail=(
                f"unexpected tool calls: {', '.join(unexpected)}"
                if unexpected
                else (f"allowed tool calls only: {', '.join(called_tools)}" if called_tools else "no tools called")
            ),
        )
    )
    for tool in expected.required_tools:
        passed = tool in called_tools
        checks.append(
            CheckResult(
                name=f"required_tool:{tool}",
                passed=passed,
                detail="required tool called" if passed else "required tool not called",
            )
        )
    return CaseResult(case=case, response=response, checks=tuple(checks))
