# Agent Trust Eval Lab v0.1.0

V0.1.0 turns repeated evidence from one personal workflow into a bounded permission recommendation for a pinned agent configuration.

## Included

1. Forty original Inbox-to-Action cases: 20 benign/adversarial pairs across four permission gates.
2. Strict system-under-test manifests and SHA-256 configuration fingerprints.
3. Repeated execution with separate unsafe-promotion, false-refusal, provider-error, and flip metrics.
4. A monotonic permission ladder with a hard `reversible_action` ceiling.
5. Native OpenAI Responses, Anthropic Messages, and Gemini `generateContent` adapters.
6. Three deterministic evaluator-conformance profiles and checked-in sample output.
7. A strict aggregate comparator that rejects incompatible inputs and omits raw trials.
8. Three dated provider baselines and one context-labeling safeguard ablation.

## Evidence at release

The deterministic profiles exercise the declared calibration paths:

| # | Profile | Trials | Recommendation |
|---:|---|---:|---|
| 1 | Safe | 120/120 passed | `reversible_action` |
| 2 | Unsafe | 117/120 passed | `read_only` |
| 3 | Unstable | 116/120 passed | `draft_only` |

These are fixture-conformance results. They prove that the evaluator handles safe, unsafe, and unstable evidence as declared. They do not measure a live model.

## Claim boundary

This release does not certify an agent or rank model brands. It evaluates the complete recorded assembly under one synthetic workflow, suite version, calibration policy, and run time.

The live-provider request and response contracts have mocked coverage. Paid endpoint verification and model findings will follow as a separately reviewed study.

## Contribution priorities

1. Challenge the permission policy and case grading.
2. Add synthetic benign/adversarial pairs for missing personal-workflow boundaries.
3. Reproduce provider compatibility issues without credentials or private data.
4. Help design Inspect AI and runtime-specific adapters without weakening the pinned-configuration model.
