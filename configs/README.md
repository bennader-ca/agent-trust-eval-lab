# Configurations

1. `demo.json` runs the full suite with deterministic fixture responses and requires no API key.
2. `demo-unsafe.json` exercises a critical-failure path.
3. `demo-unstable.json` exercises a behavioral-flip path.
4. `openai-responses.example.json` targets OpenAI's native Responses API.
5. `anthropic-messages.example.json` targets Anthropic's native Messages API.
6. `gemini-generate-content.example.json` targets Gemini's native `generateContent` API.
7. `openai-compatible.example.json` targets a generic OpenAI-style chat-completions endpoint.
8. `study-openai-terra.json` pre-registers the dated OpenAI baseline.
9. `study-anthropic-sonnet.json` pre-registers the dated Anthropic baseline.
10. `study-google-gemini.json` pre-registers the dated Gemini baseline.
11. `study-openai-terra-unlabeled-context.json` pre-registers the OpenAI context-labeling ablation.

Copy an example instead of editing it in place. Replace the model in both the SUT manifest and provider block; the CLI rejects a mismatch. Replace `model_version`, configuration name, and runtime identity with exact values.

Every live provider requires one context mode:

1. `labeled_untrusted` adds explicit untrusted-data instructions and context labels. The SUT safeguards must include `untrusted-context-labeling`.
2. `unlabeled_context` preserves the same synthetic context and user request but removes the warning and context labels. The SUT safeguards must omit `untrusted-context-labeling`.

Never put credentials in a configuration file. Set only the environment variable named by `api_key_env`.

Configuration paths are resolved relative to the configuration file, so the demo works from any current directory when given an absolute config path.
