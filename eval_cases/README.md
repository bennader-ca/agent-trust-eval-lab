# Evaluation cases

`core.json` contains seven synthetic, public-safe cases across five trust-boundary categories. Cases declare prompts, untrusted context, available tool schemas, and deterministic expectations. They never contain credentials, personal data, or instructions derived from a private production system.

The v1 schema is intentionally strict: unknown fields, duplicate IDs, malformed tool definitions, and unknown categories are rejected before a run begins.
