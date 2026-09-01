# Contributing

Contributions should make a boundary easier to understand, reproduce, or fix.

## Before opening a pull request

1. Open an issue describing the workflow, permission gate, risk category, benign neighboring behavior, and observable success/failure criteria.
2. Use only synthetic names, IDs, messages, endpoints, and tool arguments. Reserved domains such as `example.test` are preferred.
3. Add a benign/adversarial pair unless the issue explains why pairing is impossible.
4. Mark critical cases deliberately. A critical failure blocks that permission and every higher level.
5. Keep grading explicit. Explain likely false positives and false negatives.
6. Never add a real tool executor to this package.
7. Add or update standard-library tests.

Use the evaluation-case issue form for new boundaries and the provider-adapter form for sanitized compatibility reports. Security vulnerabilities belong in a private security advisory, not a public issue.

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m agent_trust_eval \
  --config configs/demo.json \
  --output reports/demo \
  --fail-on-case-failure
```

## Case checklist

- [ ] Public-safe and synthetic.
- [ ] Unique stable ID.
- [ ] Correct scenario type, risk, permission gate, criticality, and pair tag.
- [ ] Useful benign control.
- [ ] No undeclared or executable tool behavior.
- [ ] Transparent phrase/tool expectations.
- [ ] Fixture response demonstrates evaluator mechanics only.
- [ ] Documentation says what the case cannot establish.

## Prior art and licensing

Do not copy prompts, cases, datasets, or code without a specific license and attribution review. Cite conceptual influences in [Prior Art and Project Boundary](docs/prior-art.md).

Avoid provider marketing claims, opaque trust scores, private datasets, real credentials, and conclusions broader than the pinned SUT evidence.
