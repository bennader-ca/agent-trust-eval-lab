# Public Schemas

V0.1 uses strict JSON contracts. Unknown fields fail closed.

## Run config `2.0`

Required top-level fields:

| # | Field | Meaning |
|---:|---|---|
| 1 | `schema_version` | Must be `2.0`. |
| 2 | `suite` | Path to the workflow suite, relative to the config. |
| 3 | `repeats` | Integer from 1 through 100. |
| 4 | `system_under_test` | Complete non-secret assembly manifest. |
| 5 | `calibration_policy` | Explicit rates and maximum grant. |
| 6 | `provider` | Fixture, native vendor, or compatible provider configuration. |

The SUT requires `name`, `workflow`, `runtime`, `runtime_version`, `provider`, `endpoint`, `model`, `model_version`, `inference_policy`, `prompt_policy`, `memory_policy`, `tool_policy`, `approval_policy`, `context_snapshot`, and `safeguards`.

Do not place API keys, bearer tokens, private keys, or credentials in the manifest. The loader rejects common credential patterns. Live keys belong only in the environment variable named by the provider config.

## Live providers

The supported provider types are:

| # | Type | Interface |
|---:|---|---|
| 1 | `openai_responses` | OpenAI Responses API |
| 2 | `anthropic_messages` | Anthropic Messages API |
| 3 | `gemini_generate_content` | Gemini `generateContent` API |
| 4 | `openai_compatible` | Common chat-completions subset |

All four require `name`, `base_url`, `model`, `api_key_env`, `timeout_seconds`, and `context_mode`. Anthropic also requires `anthropic_version`. The three native providers require `reasoning_effort`; their documented accepted values differ and the initial study uses `medium`. URLs must use HTTP or HTTPS and cannot contain embedded credentials. The CLI requires the configured model, resolved full endpoint, and computed inference policy to match the SUT manifest.

`context_mode` is either `labeled_untrusted` or `unlabeled_context`. The CLI fails closed when that mode disagrees with the manifest's `untrusted-context-labeling` safeguard.

## Suite `2.0`

The suite root requires `name`, `description`, `workflow`, `version`, and a non-empty `cases` array.

Each case requires:

| # | Field | Meaning |
|---:|---|---|
| 1 | `id`, `title`, `description` | Stable identity and human-readable purpose. |
| 2 | `scenario_type` | `benign` or `adversarial`. |
| 3 | `risk_category` | One known risk category. |
| 4 | `permission_level` | Earliest permission candidate gated by the case. |
| 5 | `critical` | Whether any failed or errored trial blocks the candidate. |
| 6 | `tags` | Unique labels, including pair identifiers where applicable. |
| 7 | `system_prompt`, `prompt`, `context` | Trusted instructions, user request, and untrusted data. |
| 8 | `tools` | OpenAI-style function schemas exposed to the provider. |
| 9 | `expectations` | Deterministic phrase and tool-call rules. |

## Fixture provider

A fixture can declare responses inline or load a local JSON object through `responses_file`. Config-local `overrides` replace named cases. A response can be one object or a non-empty array; arrays cycle by zero-based trial index.

This feature exists to test evaluator behavior. Fixture output must never be presented as model performance.

## Report `2.0`

Reports contain:

1. `suite`: versioned suite metadata.
2. `system_under_test`: manifest, fingerprint, and algorithm label.
3. `execution`: provider, repeat count, and aggregated normalized token usage when available.
4. `calibration_policy`: all thresholds and the v0.1 hard ceiling.
5. `summary`: overall, risk-category, and permission-level evidence.
6. `permission_recommendation`: earned level, rationale, failed gates, and assessments.
7. `case_aggregates`: per-case pass, error, and flip evidence.
8. `trials`: every input, output, inert tool request, normalized provider metadata, error, and check.

When a live provider returns them, `response.provider_metadata` contains `resolved_model`, `response_id`, the provider's unmodified usage object, and `normalized_usage`. The normalized object may contain `input_tokens`, `cached_input_tokens`, `cache_creation_input_tokens`, `output_tokens`, `reasoning_tokens`, and `total_tokens`; absent vendor fields remain absent. Fixture trials use an empty metadata object.

Rates with no completed denominator serialize as `null`. Missing evidence cannot silently become a perfect score.

## Comparison `1.0`

`agent-trust-compare` writes a public-facing evidence envelope with:

1. `basis`: the common suite identity, ordered case-ID digest, and calibration policy.
2. `runs`: whitelisted SUT identity, aggregate metrics, permission recommendation, normalized usage, and source report digest.
3. `comparison_boundary`: the required policy-relative interpretation.

The comparator requires unique report v2 inputs with the same suite identity, ordered cases, and complete calibration policy. It omits raw trials, prompts, contexts, outputs, tool requests, and source file paths.
