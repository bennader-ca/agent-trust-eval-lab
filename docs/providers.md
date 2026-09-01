# Provider Adapters

V0.1 can send the same Inbox-to-Action cases through three native vendor APIs and one compatible interface. The code path is locally verified with mocked HTTP contracts. Live vendor behavior remains unverified until credentialed runs occur.

## Supported interfaces

| # | Provider type | Endpoint shape | Credential header | Normalized output |
|---:|---|---|---|---|
| 1 | `openai_responses` | `POST /v1/responses` | Bearer API key | Output text and `function_call` items |
| 2 | `anthropic_messages` | `POST /v1/messages` | `x-api-key` plus API version | Text and `tool_use` blocks |
| 3 | `gemini_generate_content` | `POST /v1beta/models/{model}:generateContent` | `x-goog-api-key` | Text and `functionCall` parts |
| 4 | `openai_compatible` | `POST /chat/completions` below the configured base | Bearer API key | Message text and tool calls |

The implementation follows the official [OpenAI Responses reference](https://developers.openai.com/api/reference/cli/resources/responses/methods/create), [Anthropic Messages reference](https://docs.anthropic.com/en/api/messages), [Anthropic tool-use guide](https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/implement-tool-use), [Gemini GenerateContent reference](https://ai.google.dev/api/generate-content), and [Gemini function-calling guide](https://ai.google.dev/gemini-api/docs/function-calling), reviewed August 31, 2026.

## Shared evaluation envelope

Every native request uses:

1. The case's trusted system prompt through the vendor's system-instruction field.
2. The same synthetic context and user request.
3. Explicit `medium` reasoning or effort, provider-native sampling defaults, and a 1,024-token output cap.
4. Non-streaming execution.
5. Vendor-native declarations for the same inert functions.
6. No tool execution or tool-result continuation.
7. `store: false` for OpenAI and Gemini, which expose that request field in their current official references.

The adapters normalize model-requested functions into `{name, arguments}`. The grader sees one shape regardless of provider. Reports also preserve the vendor's returned model identifier, response ID, and token-usage object when present, plus a comparable token-count envelope.

The common word `medium` does not imply equal reasoning compute across providers. Current Sonnet 5 and Gemini 3.7 guidance rejects non-default sampling parameters, so the native comparison uses each provider's sampling default instead of forcing temperature zero. Vendor `auto` tool-selection modes also have different semantics and eagerness. Repeated evidence measures those observed differences; it does not make the transports behaviorally identical.

The 1,024-token cap applies through different vendor accounting rules. Before the live study, confirm that each chosen model can emit the short expected answer within that cap and that hidden reasoning does not consume it.

## Context-labeling ablation

`provider.context_mode` controls one bundled context-boundary safeguard:

1. `labeled_untrusted` adds both an untrusted-data instruction and `[UNTRUSTED CONTEXT n]` prefixes.
2. `unlabeled_context` sends the same material without that warning or those labels.

The user request remains marked in both conditions. The CLI requires the first condition to include `untrusted-context-labeling` in the fingerprinted safeguard list and the second condition to omit it. V0.1 measures the instruction-plus-label bundle; it does not attribute any change to either component alone.

## Reproducibility rules

Before a live run:

1. Copy the provider example to a new ignored or private config.
2. Put the identical model ID in the provider block and SUT manifest.
3. Put the resolved full request endpoint in `system_under_test.endpoint`; validation rejects a mismatch.
4. Record the provider's published snapshot or the test date in `model_version` and bind the adapter's computed `inference_policy` into the SUT fingerprint.
5. Keep API keys only in the named environment variable.
6. Change the manifest whenever endpoint, prompt, memory, tools, approval policy, context handling, runtime, or safeguards change.
7. Run `agent-trust-eval --config path/to/config.json --validate-only` before any paid call.
8. Preserve the full generated report privately before creating a sanitized public result.

Mock contract coverage proves local serialization and parsing. It does not prove endpoint access, model compatibility, billing setup, or provider behavior.
