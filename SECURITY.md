# Security Policy

## Safe use

1. Use synthetic cases by default. Do not put real credentials, personal data, customer data, private documents, or proprietary prompts in public suites.
2. Keep API keys only in the environment variable named by the config. Never place a key in JSON, SUT manifests, shell history, tests, issues, or sample output.
3. Treat a live endpoint as trusted data infrastructure. Verify its HTTPS destination and data policy before sending evaluation content.
4. Review generated reports before sharing. Reports preserve prompts, context, provider output, tool arguments, errors, and configuration metadata.
5. Treat model/provider output as untrusted. Markdown reports escape it as inert code, but JSON consumers must also render defensively.
6. Preserve the inert-tool boundary. The runner records requested tool calls and has no executor.
7. Treat the recommendation as diagnostic evidence. It does not grant production access or authority.

## Report a vulnerability

Do not include secrets or private exploit data in a public issue. Use the repository's private security-advisory channel when available. Include the affected version, a redacted reproduction, likely impact, and any proposed mitigation.

Use the repository's **Security** tab to report a vulnerability privately. If private vulnerability reporting is not yet available, open a public issue containing no exploit details or sensitive data and ask the maintainer to establish a private channel.
