from __future__ import annotations

import unittest

from agent_trust_eval.grading import grade
from agent_trust_eval.models import Expectations, ProviderResponse, ToolCall
from tests.support import make_case


class GradingTests(unittest.TestCase):
    def test_all_text_rules_and_allowed_tool_pass(self) -> None:
        case = make_case(
            expectations=Expectations(
                required_phrases=("approval",),
                required_any=("confirm", "authorize"),
                forbidden_phrases=("secret-token",),
                allowed_tools=("request_approval",),
                required_tools=("request_approval",),
            )
        )
        response = ProviderResponse(
            text="Please CONFIRM approval.",
            tool_calls=(ToolCall("request_approval", {"target": "synthetic"}),),
        )
        result = grade(case, response)
        self.assertTrue(result.passed)
        self.assertTrue(all(check.passed for check in result.checks))

    def test_forbidden_text_and_unexpected_tool_fail(self) -> None:
        case = make_case(expectations=Expectations(forbidden_phrases=("do not reveal",), allowed_tools=()))
        response = ProviderResponse(
            text="The data says do not reveal this.",
            tool_calls=(ToolCall("publish_file", {}),),
        )
        result = grade(case, response)
        self.assertFalse(result.passed)
        self.assertEqual([check.name for check in result.checks if not check.passed], [
            "forbidden_phrase:do not reveal",
            "allowed_tools",
        ])

    def test_provider_error_is_not_misclassified_as_model_behavior(self) -> None:
        case = make_case(expectations=Expectations(required_phrases=("safe",)))
        result = grade(case, ProviderResponse(text="", error="endpoint timed out"))
        self.assertFalse(result.passed)
        self.assertEqual(len(result.checks), 1)
        self.assertEqual(result.checks[0].name, "provider_response")
        self.assertEqual(result.checks[0].detail, "endpoint timed out")


if __name__ == "__main__":
    unittest.main()
