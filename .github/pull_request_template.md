## Purpose

Describe the boundary, failure, safeguard, or reproducibility improvement this change addresses.

## Evidence

List the exact tests, fixture outcomes, or sanitized live evidence supporting the change.

## Checklist

- [ ] I used only synthetic, public-safe data.
- [ ] I added a benign neighbor for any adversarial case, or explained why pairing is impossible.
- [ ] I kept tool calls inert and added no executor.
- [ ] I documented likely false positives, false negatives, and claim boundaries.
- [ ] I reviewed licenses and attributed any reused material.
- [ ] `PYTHONPATH=src python3 -m unittest discover -s tests -v` passes.
- [ ] I reviewed generated reports for credentials, personal data, and active markup.
