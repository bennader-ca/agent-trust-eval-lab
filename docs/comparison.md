# Comparing Runs

`agent-trust-compare` turns two or more compatible report v2 files into a compact evidence table for review or publication.

```bash
agent-trust-compare \
  reports/openai/report.json \
  reports/anthropic/report.json \
  reports/gemini/report.json \
  --output reports/comparison
```

The command writes `comparison.json` and `comparison.md`. It includes configuration identities, recommendations, error and stability metrics, normalized token totals, and each source report's SHA-256 digest.

## Compatibility checks

The command refuses a comparison unless every report uses:

1. Report schema `2.0`.
2. The same suite name, workflow, version, case count, and ordered case-ID digest.
3. The same complete calibration policy.
4. A unique source report.

These checks make the permission labels comparable under one declared policy. They do not make the configurations causally identical.

## Publication boundary

The comparison artifacts copy only whitelisted aggregate evidence. They omit raw trials, prompts, contexts, model outputs, tool requests, and local source paths.

Review every source report before publishing. A comparison can still reveal model names, configuration names, safeguards, fingerprints, timestamps, token counts, and behavioral results.

Do not use the output to claim a universal winner or safety certification. A valid finding names the suite version, configuration fingerprint, calibration policy, repeats, and observed permission recommendation.
