# Limitations

V0.1 supports bounded regression evidence. It cannot prove that a model, agent, or deployment is safe.

## Known limits

1. **Phrase grading is shallow.** A semantically correct answer can miss an expected phrase. A bad answer can repeat the right keyword. Tool-name checks do not yet validate arguments against case-specific constraints.
2. **Cases are synthetic and single-turn.** The suite does not represent every inbox, language, culture, attack, or long-horizon interaction.
3. **The workflow is narrow.** Inbox-to-Action does not establish permission fitness for finance, health, coding, browsing, calendar, or other workflows.
4. **Tools never execute.** The runner records requests but does not simulate results, retries, chained actions, rollback, or side effects.
5. **Thresholds are policy choices.** A `reversible_action` recommendation means the observed evidence met the included policy. It is not a scientific constant or operational authorization.
6. **The manifest is self-declared.** Its fingerprint identifies the declared configuration but does not attest the deployed runtime.
7. **Repeated calls are not independent proof.** Flip rate exposes simple run variation. It does not provide confidence intervals, causal attribution, or immunity to provider updates.
8. **Provider behavior can drift.** Models, system prompts, APIs, safety layers, and tool schemas can change after a run. Pin exact versions where possible and rerun regressions.
9. **Native adapters are contract-tested, not endpoint-verified.** Mocked tests cover OpenAI Responses, Anthropic Messages, and Gemini `generateContent` request/response shapes. Paid endpoints may still expose model-specific restrictions, policy blocks, or schema changes.
10. **No live findings ship yet.** The checked-in 120/120 result comes from curated fixture responses. It is evaluator conformance evidence, not LLM performance.
11. **No certification.** Passing cases cannot replace threat modeling, access control, sandboxing, audit logs, incident response, or human review.
12. **Transport parity is approximate.** The adapters align a named reasoning level, output cap, context, and inert functions, but vendor reasoning controls, sampling defaults, APIs, and safety layers are not semantically identical.
13. **Repeated settings are not deterministic.** Infrastructure, routing, sampling, implementation, and provider changes can still produce flips.
14. **The output cap can affect models differently.** Some models count hidden reasoning against output limits, which can truncate visible text and create misleading failures.
15. **Resolved model metadata is evidence, not attestation.** Reports preserve the vendor-returned model identifier when available, but v0.1 does not automatically prove that it equals a self-declared `model_version`.

## Appropriate use

Use v0.1 to:

1. Make a personal-workflow authority policy explicit.
2. Reproduce a known boundary failure.
3. Compare one safeguard or configuration change.
4. Create a transparent regression test.
5. Generate hypotheses for deeper red teaming.

Do not use the output as permission to expose production data or execute consequential actions.
