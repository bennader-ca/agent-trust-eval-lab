# Initial Live Study Protocol

The first public study should compare pinned configurations in two layers: a controlled three-provider baseline, then one context-labeling safeguard ablation. This produces useful evidence without claiming a universal model winner.

## Research questions

1. Under the same Inbox-to-Action suite, disclosed policy, prompt, tools, context labeling, output cap, and repeat count, what permission does each pinned provider/model configuration earn?
2. Within one pinned provider/model configuration, how does removing explicit untrusted-context labeling change unsafe promotion, false refusal, and stability?

## Pre-register before spending credits

| # | Field | Freeze before the primary run |
|---:|---|---|
| 1 | Suite | `inbox_to_action` version `0.1.0`, 40 cases |
| 2 | Models | Exact vendor model IDs and available snapshots |
| 3 | Runtime | Native adapter, explicit medium reasoning, provider sampling default, 1,024-token cap, non-streaming |
| 4 | Repeats | Five per case for primary evidence |
| 5 | Policy | The checked-in v0.1 calibration thresholds |
| 6 | Baseline safeguard | `context_mode: labeled_untrusted` |
| 7 | Ablation | Same configuration with `context_mode: unlabeled_context` and matching manifest |
| 8 | Review rule | Inspect every failure, provider error, and flipped case before publication |

## Cost-controlled run sequence

1. Review the four dated study configs. They pre-register three provider baselines and one OpenAI context-labeling ablation. Do not edit them after beginning the study; record any necessary revision as a new dated config.
2. Run each config with `--validate-only`. This verifies the suite, manifest binding, model match, context safeguard, and provider schema without reading a key or making a paid call.
3. Run the three baselines with `--repeats 1` without editing their files. This smoke phase makes 120 total API calls and produces no publishable comparison.
4. Stop if any provider error suggests an authentication, model, schema, quota, output-cap, or transport problem. Compare the returned `resolved_model` and usage metadata with the declared manifest. Fix or update the pre-registration and restart all affected conditions.
5. Restore `repeats` to `5`. The three-provider baseline makes 600 calls: 200 per provider.
6. Run `study-openai-terra-unlabeled-context.json`. Its checked-in diff changes only the disclosed configuration identity, runtime version, safeguard list, and `context_mode`. This adds 200 calls.
7. Review raw trials. If a deterministic phrase rule misgrades a semantically correct answer, document the issue and rerun every affected condition after the rubric change.
8. Generate `comparison.json` and `comparison.md` with `agent-trust-compare`. Publish sanitized artifacts only after the configurations, fingerprints, suite, policy, review notes, and comparison totals agree.

The planned first study therefore uses 120 smoke calls and 800 primary calls. The model choice and current price assumptions are pre-registered in [Initial Model Cohort and Cost Pre-registration](model-selection-2026-08-31.md). Do not use a reasoning-heavy model whose hidden tokens exhaust the 1,024-token cap during smoke testing.

## Copy-ready commands

Validate all pre-registered conditions without reading API keys:

```bash
agent-trust-eval --config configs/study-openai-terra.json --validate-only
agent-trust-eval --config configs/study-anthropic-sonnet.json --validate-only
agent-trust-eval --config configs/study-google-gemini.json --validate-only
agent-trust-eval --config configs/study-openai-terra-unlabeled-context.json --validate-only
```

Run the three-provider smoke phase without changing the files:

```bash
agent-trust-eval --config configs/study-openai-terra.json --repeats 1 --output reports/smoke/openai
agent-trust-eval --config configs/study-anthropic-sonnet.json --repeats 1 --output reports/smoke/anthropic
agent-trust-eval --config configs/study-google-gemini.json --repeats 1 --output reports/smoke/gemini
```

After smoke review and spend approval, run the four primary conditions:

```bash
agent-trust-eval --config configs/study-openai-terra.json --output reports/primary/openai
agent-trust-eval --config configs/study-anthropic-sonnet.json --output reports/primary/anthropic
agent-trust-eval --config configs/study-google-gemini.json --output reports/primary/gemini
agent-trust-eval --config configs/study-openai-terra-unlabeled-context.json --output reports/primary/openai-unlabeled
agent-trust-compare \
  reports/primary/openai/report.json \
  reports/primary/anthropic/report.json \
  reports/primary/gemini/report.json \
  reports/primary/openai-unlabeled/report.json \
  --output reports/primary/comparison
```

## Interpretation

Provider APIs differ even when prompts and tools appear aligned. Report the result as bounded evidence:

> For Inbox-to-Action suite v0.1.0, pinned configuration `[fingerprint]` earned `[permission]` under calibration policy `[policy]` across `[trials]` trials.

Do not write “model X is trustworthy,” “model X is safest,” or “the eval proves safety.” Compare configuration fingerprints, disclose provider errors and grader limitations, and separate observed behavior from inference.

## Publication gate

The GitHub release may ship before live results if every fixture is labeled correctly. The findings post requires sanitized reports, a live repository URL, exact numeric reconciliation, and Ben's approval.
