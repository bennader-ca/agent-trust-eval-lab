# Roadmap

V0.1 ships the smallest useful vertical slice: pinned SUT identity, 40 paired Inbox-to-Action cases, repeated runs, transparent scoring, and permission calibration.

## V0.1 launch gates

1. Publish the reviewed repository under Ben's GitHub account.
2. Add direct repository URLs to package metadata.
3. Run and inspect credentialed baseline and safeguard-ablation configurations.
4. Publish only bounded findings tied to SUT fingerprints and suite version.

## V0.1.1 — Live-study readiness

1. Verify the native OpenAI Responses adapter against a paid endpoint.
2. Verify the native Anthropic Messages adapter against a paid endpoint.
3. Verify the native Gemini `generateContent` adapter against a paid endpoint.
4. Capture sanitized response IDs, resolved model versions, token use, and request timing.
5. Add a reviewed public live-run bundle using the existing machine-readable comparator.

The local v0.1 adapters already normalize native text, inert function calls, and token usage; bind explicit medium reasoning and provider-native sampling into the fingerprint; cap output at 1,024 tokens; and expose a context-labeling ablation.

## V0.3 — Stronger evidence

1. Tool-argument and structured-output checks.
2. Pairwise and metamorphic consistency checks.
3. Optional disclosed semantic grader.
4. Confidence intervals and longitudinal drift comparison.
5. Selective tags and case packs.

## V0.4 — Runtime adapters

1. Inspect AI task export or adapter.
2. OpenClaw assembly runner.
3. Codex and Claude Code configuration adapters where their interfaces permit controlled evaluation.
4. Configuration-diff reports for safeguard ablations.

## Later workflow packs

1. Calendar-to-Commitment.
2. Document-to-Decision.
3. Memory-to-Recommendation.
4. Research-to-External-Action.

Future work should make failures easier to reproduce and fix. It should not chase a broad model leaderboard.
