# Release Checklist

The local repository can become a public v0.1 after the external gates below are complete.

## Verified locally

- [x] Strict v2 SUT, suite, config, and report contracts.
- [x] Forty original Inbox-to-Action cases with 20 benign/adversarial pairs.
- [x] Three repeated fixture profiles exercising safe, unsafe, and unstable paths.
- [x] Deterministic permission recommendation and hard reversible-action ceiling.
- [x] Tests, clean install path, installed CLI, JSON reports, Markdown escaping, and public-data scans.
- [x] README, method, schemas, limitations, prior art, security, contribution, and roadmap documents.
- [x] MIT license and GitHub Actions workflow.
- [x] Mock-tested native OpenAI Responses, Anthropic Messages, and Gemini `generateContent` transports.
- [x] Executable labeled-versus-unlabeled context safeguard ablation with manifest consistency checks.
- [x] Per-trial resolved model, response ID, and usage capture when returned by a live provider.
- [x] Normalized token accounting and aggregated report totals while preserving raw vendor usage.
- [x] Dated balanced-model cohort, inference settings, pricing assumptions, and spend review threshold.
- [x] Strict machine-readable cross-run comparison with source hashes and raw-trial omission.
- [x] Immutable smoke-run repeat override and checked-in safeguard-ablation config.
- [x] Copy-ready live-study commands and bounded v0.1.0 release notes.

## Required before GitHub publication

- [x] Ben creates the GitHub account `bennader-ca`.
- [ ] Confirm 2FA or a passkey is enabled before release.
- [x] Repository owner and slug selected: `bennader-ca/agent-trust-eval-lab`.
- [x] Add the final repository URLs to `pyproject.toml`.
- [x] Initialize the first reviewed commit and confirm the 65-file public inventory.
- [x] Create the approved public repository with the agreed name, description, and visibility.
- [ ] Push, confirm GitHub Actions passes, and create the `v0.1.0` release tag only after review.

## Required before publishing model findings

- [x] Add direct provider adapters for the three planned vendors.
- [ ] Verify each adapter against its paid endpoint before treating it as live-ready.
- [ ] Confirm the chosen models accept the pre-registered medium reasoning settings and can answer within the 1,024-token cap.
- [ ] Reconcile returned model identifiers with each declared `model_version` after smoke runs.
- [ ] Store API keys only in environment variables or the approved local secret store.
- [x] Pre-register the SUT manifests, suite version, repeats, inference policy, and calibration policy.
- [ ] Run baseline and safeguard-ablation configurations.
- [ ] Review every failed and flipped trial for grader error.
- [ ] Sanitize reports and exclude credentials, private data, and unnecessary raw content.
- [ ] State conclusions only for the recorded SUT fingerprints and workflow.
- [ ] Do not say “I trust LLM X” or imply certification.

## Required before LinkedIn publication

- [ ] Ben reviews and approves the final post.
- [ ] The GitHub URL and public release are live.
- [ ] Every numeric claim matches a published sanitized report.
- [ ] The post acknowledges prior art and describes the narrower contribution.
- [ ] The contributor invitation names specific useful next steps.

No automated process may create the account, publish the repository, or post to LinkedIn without Ben's explicit approval.
