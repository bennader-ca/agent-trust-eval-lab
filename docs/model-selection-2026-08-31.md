# Initial model cohort and cost pre-registration

Status: proposed baseline, checked against official vendor documentation on 2026-08-31.

## Decision

The first public study will compare three current, balanced production models:

| # | Provider | Model | Why it is in the cohort | Reasoning control | Standard paid input / output price per 1M tokens |
|---:|---|---|---|---|---:|
| 1 | OpenAI | `gpt-5.6-terra` | OpenAI describes Terra as the GPT-5.6 option that balances intelligence and cost. | `medium` | $2 / $12 |
| 2 | Anthropic | `claude-sonnet-5` | Anthropic describes Sonnet 5 as its best combination of speed and intelligence. | `medium` effort with adaptive thinking | $2 / $10 |
| 3 | Google | `gemini-3.7-flash` | Google describes 3.7 Flash as its current production workhorse for coding and agents. | `medium` thinking | $0.75 / $3.75 through 2026-12-31 |

Sources: [OpenAI model guide](https://developers.openai.com/api/docs/models), [GPT-5.6 Terra](https://developers.openai.com/api/docs/models/gpt-5.6-terra), [OpenAI API pricing](https://developers.openai.com/api/docs/pricing), [Anthropic models](https://docs.anthropic.com/en/docs/about-claude/models/overview), [Claude Sonnet 5](https://docs.anthropic.com/en/docs/models/sonnet-5/overview), [Anthropic pricing](https://docs.anthropic.com/en/docs/about-claude/pricing), [Gemini 3.7 Flash](https://ai.google.dev/gemini-api/docs/latest-model), and [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing).

This is a comparison of deployable balanced-tier choices, not each vendor's most capable or most expensive model. It answers a practical question: which pinned agent configuration earns which permission level for this workflow under a reasonable operating budget?

## Controls held constant

- Same 40 public cases and case order.
- Five independent trials per case in the primary run.
- Single-turn memory policy.
- Same system prompt and context construction.
- Same inert function declarations; the harness records requested tool calls but executes none.
- Same 1,024-token response cap and non-streaming transport.
- Explicit `medium` reasoning or effort.
- Provider-native sampling defaults. Current Sonnet 5 and Gemini 3.7 guidance rejects non-default sampling parameters, so the study does not force `temperature: 0` on any native adapter.
- No server-side response storage where the API exposes a request field for it.

The word `medium` is not a claim that the vendors allocate equal reasoning compute. It is the nearest shared, documented setting and remains part of each system-under-test fingerprint. OpenAI supports configurable reasoning effort for Terra; Anthropic describes medium as a balanced step-down; Google documents medium as the default balanced thinking level for Gemini 3.7 Flash. See [Anthropic effort controls](https://docs.anthropic.com/en/docs/build-with-claude/effort) and [Gemini thinking controls](https://ai.google.dev/gemini-api/docs/generate-content/thinking).

## Cost control

The smoke stage is 120 calls: 40 cases × one trial × three models. The baseline primary stage is 600 calls: 40 cases × five trials × three models. One safeguard ablation adds 200 calls only after the baseline is accepted.

At the 1,024-token response cap, the maximum listed-price output charge is approximately:

| # | Stage | OpenAI | Anthropic | Google | Total |
|---:|---|---:|---:|---:|---:|
| 1 | Smoke plus baseline primary, 240 calls per provider | $2.95 | $2.46 | $0.92 | $6.33 |
| 2 | One 200-call ablation | up to $2.46 | up to $2.05 | up to $0.77 | provider dependent |

Those figures exclude input tokens and any pricing or accounting differences not represented by the visible response cap. The reports therefore preserve the raw vendor usage object and add normalized input, output, reasoning, cached-input, and total counters when returned.

Planning threshold: do not start the 600-call primary run if smoke usage projects the complete baseline plus one ablation above $20 without a fresh budget decision. Vendor account spend limits remain the stronger control.

## Interpretation boundary

The study may support a statement such as:

> For this 40-case personal inbox-to-action workflow, with this pinned prompt, context treatment, tool boundary, approval policy, model, and inference setting, configuration X earned a higher bounded permission recommendation than configurations Y and Z.

It cannot support “model X is trustworthy,” “provider X is safest,” or a general ranking of OpenClaw, Claude Code, Codex, or other agent runtimes. Runtime-specific evaluations require separate pinned manifests and suites.

## Re-check before paid calls

1. Confirm all three model IDs remain available to the paid accounts.
2. Re-check official pricing and model lifecycle pages on the run date.
3. Run `--validate-only` for all three checked-in study configs.
4. Run one 40-case smoke pass per provider.
5. Inspect returned model identifiers, provider errors, output truncation, and normalized usage.
6. Record any deviation as a new fingerprint and update this pre-registration before restarting affected conditions.
