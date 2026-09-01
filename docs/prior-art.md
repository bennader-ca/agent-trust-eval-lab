# Prior Art and Project Boundary

Agent Trust Eval Lab builds on a mature open-source evaluation field. It does not claim to be the first agent eval, prompt-injection benchmark, personal-assistant benchmark, or governance test.

License observations below were checked from primary repositories on August 31, 2026. Recheck upstream terms before reusing code or data.

| # | Project | Relevant contribution | License observed | Boundary versus this project |
|---:|---|---|---|---|
| 1 | [Inspect AI](https://github.com/UKGovernmentBEIS/inspect_ai) | Extensible model evaluations, tool use, multi-turn work, model-graded scoring, and a large eval library. | MIT | A mature general evaluation engine. Agent Trust Eval Lab remains a small standalone suite and calibration layer; Inspect compatibility is roadmap work. |
| 2 | [Promptfoo](https://github.com/promptfoo/promptfoo) | Multi-provider prompt and agent comparison, red teaming, CI integration, and vulnerability testing. | MIT | Already solves broad provider comparison and red teaming. This project focuses on personal-workflow permission recommendations. |
| 3 | [AgentDojo](https://github.com/ethz-spylab/agentdojo) | Dynamic tool-agent evaluation under indirect prompt injection, with utility and security measured separately. | MIT | Inspired the separation of benign utility and adversarial security. No AgentDojo code, cases, or data are copied. |
| 4 | [InjecAgent](https://github.com/uiuc-kang-lab/InjecAgent) | A large indirect prompt-injection benchmark for tool-integrated agents. | MIT | Demonstrates injection breadth at a scale v0.1 does not attempt. This suite contains a smaller set of original workflow-specific injection cases. |
| 5 | [AgentCIBench](https://github.com/UKPLab/arxiv2026-agentcibench) | Contextual-integrity failures across personal applications, including overshare and recipient mismatch. | Apache-2.0 code; CC BY 4.0 data | Closest conceptual neighbor for personal-app privacy. This project adds a broader permission ladder across one workflow and uses original synthetic cases. |
| 6 | [Pi-Bench](https://github.com/Simplified-Reasoning/Pi-Bench) | Proactive personal assistants in long-horizon, persistent workflows. | Apache-2.0 | Covers richer longitudinal utility than this single-turn suite. Agent Trust Eval Lab concentrates on bounded authority and restraint. |
| 7 | [AgentGovBench](https://github.com/agentic-control-plane/agentgovbench) | Governance-layer scenarios for identity, policy, delegation, audit, fail modes, and multiple runtime integrations. | MIT | Tests infrastructure around agents. This project maps observed personal-workflow behavior to a policy-relative permission recommendation. |

## What v0.1 adds

1. One inspectable 40-case personal workflow with benign/adversarial pairs at every permission gate.
2. A required system-under-test manifest and stable configuration fingerprint.
3. Separate unsafe-promotion, false-refusal, provider-error, and flip evidence.
4. A monotonic, machine-readable recommendation from `prohibited` through `reversible_action`.
5. Safe, unsafe, and unstable conformance profiles that prove the calibrator behaves as declared.

## What v0.1 does not reuse

V0.1 copies no third-party code, prompts, scenarios, datasets, or model outputs. Its cases and fixture responses are original synthetic material. The listed projects informed problem framing and design choices and deserve explicit credit.

Future integrations or dataset reuse must review the exact upstream license, version, attribution, and distribution requirements at that time.
