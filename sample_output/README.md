# Sample output

`report.json` and `report.md` are generated from `configs/demo.json`. They demonstrate the v1 schema and expected safe path using curated fixture responses; they are not measurements of a real model.

Response decisions are deterministic. The `generated_at` field records when the checked-in example was produced and will differ in a new run.

`profiles.md` shows the expected aggregate differences across the three fixture profiles. Recreate a machine-readable version with `agent-trust-compare` after generating all three reports; see [Comparing Runs](../docs/comparison.md).
