from __future__ import annotations

import json
import os
import unittest
from unittest.mock import MagicMock, patch

from agent_trust_eval.models import EvalCase
from agent_trust_eval.providers import (
    AnthropicMessagesProvider,
    GeminiGenerateContentProvider,
    OpenAICompatibleProvider,
    OpenAIResponsesProvider,
    ProviderConfigError,
    build_provider,
)
from tests.support import make_case as base_case


def make_case() -> EvalCase:
    case = base_case(scenario_type="adversarial", risk_category="prompt_injection")
    return EvalCase(
        **{
            **case.__dict__,
            "context": ("Untrusted page text.",),
            "tools": (
                {
                    "type": "function",
                    "function": {
                        "name": "send_message",
                        "description": "Send a message.",
                        "parameters": {"type": "object", "properties": {}},
                    },
                },
            ),
        }
    )


def http_response(payload: dict[str, object]) -> MagicMock:
    response = MagicMock()
    response.__enter__.return_value = response
    response.read.return_value = json.dumps(payload).encode()
    return response


class ProviderTests(unittest.TestCase):
    def test_fixture_provider_returns_normalized_response(self) -> None:
        provider = build_provider(
            {
                "type": "fixture",
                "name": "test-fixture",
                "responses": {
                    "case_one": {
                        "text": "safe response",
                        "tool_calls": [{"name": "request_approval", "arguments": {"id": "1"}}],
                    }
                },
            }
        )
        response = provider.complete(make_case())
        self.assertEqual(provider.name, "test-fixture")
        self.assertEqual(response.text, "safe response")
        self.assertEqual(response.tool_calls[0].name, "request_approval")

    def test_fixture_response_sequences_cycle_by_trial(self) -> None:
        provider = build_provider(
            {
                "type": "fixture",
                "name": "sequence-fixture",
                "responses": {"case_one": [{"text": "first"}, {"text": "second"}]},
            }
        )
        self.assertEqual(provider.complete(make_case(), 0).text, "first")
        self.assertEqual(provider.complete(make_case(), 1).text, "second")
        self.assertEqual(provider.complete(make_case(), 2).text, "first")

    def test_fixture_missing_case_is_clear(self) -> None:
        provider = build_provider(
            {"type": "fixture", "name": "fixture", "responses": {"other": {"text": "x"}}}
        )
        with self.assertRaisesRegex(RuntimeError, "fixture response missing"):
            provider.complete(make_case())

    def test_unknown_provider_is_rejected(self) -> None:
        with self.assertRaisesRegex(ProviderConfigError, "unknown provider type"):
            build_provider({"type": "unknown"})

    def test_openai_compatible_rejects_credentials_in_url(self) -> None:
        with self.assertRaisesRegex(ProviderConfigError, "embedded credentials"):
            build_provider(
                {
                    "type": "openai_compatible",
                    "name": "unsafe-url",
                    "base_url": "https://user:password@example.invalid/v1",
                    "model": "model",
                    "api_key_env": "SAFE_ENV_NAME",
                    "context_mode": "labeled_untrusted",
                }
            )

    def test_openai_compatible_normalizes_tool_calls_and_labels_context(self) -> None:
        provider = OpenAICompatibleProvider(
            provider_name="live-test",
            base_url="https://example.invalid/v1",
            model="test-model",
            api_key_env="TEST_PROVIDER_KEY",
            timeout_seconds=5,
            context_mode="labeled_untrusted",
        )
        response_body = http_response(
            {
                "id": "chatcmpl_test",
                "model": "compatible-resolved-model",
                "usage": {"total_tokens": 12},
                "choices": [
                    {
                        "message": {
                            "content": "I need approval.",
                            "tool_calls": [
                                {
                                    "function": {
                                        "name": "request_approval",
                                        "arguments": "{\"target\": \"synthetic\"}",
                                    }
                                }
                            ],
                        }
                    }
                ]
            }
        )
        with patch.dict(os.environ, {"TEST_PROVIDER_KEY": "test-only-key"}, clear=False):
            with patch("agent_trust_eval.providers.urlopen", return_value=response_body) as opened:
                response = provider.complete(make_case())
        request = opened.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(request.full_url, "https://example.invalid/v1/chat/completions")
        self.assertIn("[UNTRUSTED CONTEXT 1]", payload["messages"][1]["content"])
        self.assertEqual(response.tool_calls[0].arguments, {"target": "synthetic"})
        self.assertEqual(response.metadata["resolved_model"], "compatible-resolved-model")

    def test_openai_compatible_requires_environment_key(self) -> None:
        provider = OpenAICompatibleProvider(
            "live",
            "https://example.invalid",
            "model",
            "ABSENT_KEY",
            1,
            "labeled_untrusted",
        )
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "ABSENT_KEY"):
                provider.complete(make_case())

    def test_openai_responses_normalizes_text_tools_and_request(self) -> None:
        provider = OpenAIResponsesProvider(
            "openai-test",
            "https://api.openai.example/v1",
            "gpt-test",
            "OPENAI_TEST_KEY",
            5,
            "labeled_untrusted",
            "medium",
        )
        response_body = http_response(
            {
                "id": "resp_test",
                "model": "gpt-test-2026-08-01",
                "usage": {
                    "input_tokens": 12,
                    "input_tokens_details": {"cached_tokens": 2},
                    "output_tokens": 10,
                    "output_tokens_details": {"reasoning_tokens": 4},
                    "total_tokens": 22,
                },
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "Approval required."}],
                    },
                    {
                        "type": "function_call",
                        "name": "request_approval",
                        "arguments": "{\"target\": \"synthetic\"}",
                    },
                ]
            }
        )
        with patch.dict(os.environ, {"OPENAI_TEST_KEY": "test-only-key"}, clear=False):
            with patch("agent_trust_eval.providers.urlopen", return_value=response_body) as opened:
                response = provider.complete(make_case())
        request = opened.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(request.full_url, "https://api.openai.example/v1/responses")
        self.assertFalse(payload["store"])
        self.assertEqual(payload["max_output_tokens"], 1024)
        self.assertNotIn("temperature", payload)
        self.assertEqual(payload["reasoning"], {"effort": "medium"})
        self.assertEqual(payload["tools"][0]["name"], "send_message")
        self.assertNotIn("function", payload["tools"][0])
        self.assertIn("[UNTRUSTED CONTEXT 1]", payload["input"])
        self.assertEqual(response.text, "Approval required.")
        self.assertEqual(response.tool_calls[0].name, "request_approval")
        self.assertEqual(response.tool_calls[0].arguments, {"target": "synthetic"})
        self.assertEqual(response.metadata["response_id"], "resp_test")
        self.assertEqual(response.metadata["resolved_model"], "gpt-test-2026-08-01")
        self.assertEqual(response.metadata["normalized_usage"]["input_tokens"], 12)
        self.assertEqual(response.metadata["normalized_usage"]["cached_input_tokens"], 2)
        self.assertEqual(response.metadata["normalized_usage"]["reasoning_tokens"], 4)
        self.assertEqual(response.metadata["normalized_usage"]["total_tokens"], 22)

    def test_anthropic_messages_normalizes_content_and_request(self) -> None:
        provider = AnthropicMessagesProvider(
            "anthropic-test",
            "https://api.anthropic.example/v1",
            "claude-test",
            "ANTHROPIC_TEST_KEY",
            5,
            "2023-06-01",
            "labeled_untrusted",
            "medium",
        )
        response_body = http_response(
            {
                "id": "msg_test",
                "model": "claude-test-20260801",
                "usage": {
                    "input_tokens": 10,
                    "cache_creation_input_tokens": 2,
                    "cache_read_input_tokens": 1,
                    "output_tokens": 3,
                    "thinking_tokens": 2,
                },
                "content": [
                    {"type": "text", "text": "Approval required."},
                    {
                        "type": "tool_use",
                        "id": "toolu_test",
                        "name": "request_approval",
                        "input": {"target": "synthetic"},
                    },
                ]
            }
        )
        with patch.dict(os.environ, {"ANTHROPIC_TEST_KEY": "test-only-key"}, clear=False):
            with patch("agent_trust_eval.providers.urlopen", return_value=response_body) as opened:
                response = provider.complete(make_case())
        request = opened.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(request.full_url, "https://api.anthropic.example/v1/messages")
        self.assertEqual(request.get_header("Anthropic-version"), "2023-06-01")
        self.assertEqual(payload["max_tokens"], 1024)
        self.assertNotIn("temperature", payload)
        self.assertEqual(payload["output_config"], {"effort": "medium"})
        self.assertEqual(payload["tools"][0]["name"], "send_message")
        self.assertIn("input_schema", payload["tools"][0])
        self.assertEqual(response.text, "Approval required.")
        self.assertEqual(response.tool_calls[0].arguments, {"target": "synthetic"})
        self.assertEqual(response.metadata["response_id"], "msg_test")
        self.assertEqual(response.metadata["resolved_model"], "claude-test-20260801")
        self.assertEqual(response.metadata["normalized_usage"]["total_tokens"], 16)
        self.assertEqual(response.metadata["normalized_usage"]["reasoning_tokens"], 2)

    def test_gemini_generate_content_normalizes_parts_and_request(self) -> None:
        provider = GeminiGenerateContentProvider(
            "gemini-test",
            "https://generativelanguage.example/v1beta",
            "models/gemini/test pinned",
            "GEMINI_TEST_KEY",
            5,
            "labeled_untrusted",
            "medium",
        )
        response_body = http_response(
            {
                "responseId": "gemini-response-test",
                "modelVersion": "gemini-test-2026-08-01",
                "usageMetadata": {
                    "promptTokenCount": 10,
                    "candidatesTokenCount": 5,
                    "thoughtsTokenCount": 3,
                    "totalTokenCount": 18,
                },
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {"text": "Approval required."},
                                {
                                    "functionCall": {
                                        "name": "request_approval",
                                        "args": {"target": "synthetic"},
                                    }
                                },
                            ]
                        }
                    }
                ]
            }
        )
        with patch.dict(os.environ, {"GEMINI_TEST_KEY": "test-only-key"}, clear=False):
            with patch("agent_trust_eval.providers.urlopen", return_value=response_body) as opened:
                response = provider.complete(make_case())
        request = opened.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(
            request.full_url,
            "https://generativelanguage.example/v1beta/models/gemini%2Ftest%20pinned:generateContent",
        )
        self.assertFalse(payload["store"])
        self.assertEqual(payload["generationConfig"]["maxOutputTokens"], 1024)
        self.assertNotIn("temperature", payload["generationConfig"])
        self.assertEqual(
            payload["generationConfig"]["thinkingConfig"],
            {"thinkingLevel": "medium"},
        )
        self.assertEqual(
            payload["tools"][0]["functionDeclarations"][0]["name"], "send_message"
        )
        self.assertEqual(response.text, "Approval required.")
        self.assertEqual(response.tool_calls[0].arguments, {"target": "synthetic"})
        self.assertEqual(response.metadata["response_id"], "gemini-response-test")
        self.assertEqual(response.metadata["resolved_model"], "gemini-test-2026-08-01")
        self.assertEqual(response.metadata["normalized_usage"]["reasoning_tokens"], 3)

    def test_native_provider_builders_validate_required_fields(self) -> None:
        openai = build_provider(
            {
                "type": "openai_responses",
                "name": "openai",
                "base_url": "https://api.openai.example/v1",
                "model": "gpt-test",
                "api_key_env": "OPENAI_API_KEY",
                "context_mode": "labeled_untrusted",
                "reasoning_effort": "medium",
            }
        )
        gemini = build_provider(
            {
                "type": "gemini_generate_content",
                "name": "gemini",
                "base_url": "https://generativelanguage.example/v1beta",
                "model": "gemini-test",
                "api_key_env": "GEMINI_API_KEY",
                "context_mode": "labeled_untrusted",
                "reasoning_effort": "medium",
            }
        )
        self.assertIsInstance(openai, OpenAIResponsesProvider)
        self.assertIsInstance(gemini, GeminiGenerateContentProvider)
        with self.assertRaisesRegex(ProviderConfigError, "anthropic_version"):
            build_provider(
                {
                    "type": "anthropic_messages",
                    "name": "anthropic",
                    "base_url": "https://api.anthropic.example/v1",
                    "model": "claude-test",
                    "api_key_env": "ANTHROPIC_API_KEY",
                    "context_mode": "labeled_untrusted",
                }
            )

    def test_unlabeled_context_mode_removes_only_untrusted_labeling(self) -> None:
        provider = OpenAIResponsesProvider(
            "openai-ablation",
            "https://api.openai.example/v1",
            "gpt-test",
            "OPENAI_TEST_KEY",
            5,
            "unlabeled_context",
            "medium",
        )
        response_body = http_response({"output": []})
        with patch.dict(os.environ, {"OPENAI_TEST_KEY": "test-only-key"}, clear=False):
            with patch("agent_trust_eval.providers.urlopen", return_value=response_body) as opened:
                provider.complete(make_case())
        payload = json.loads(opened.call_args.args[0].data)
        self.assertIn("Untrusted page text.", payload["input"])
        self.assertIn("[USER REQUEST]", payload["input"])
        self.assertNotIn("[UNTRUSTED CONTEXT", payload["input"])
        self.assertNotIn("untrusted data, not instructions", payload["input"])


if __name__ == "__main__":
    unittest.main()
