from __future__ import annotations

import unittest

from agent_trust_eval.manifest import (
    ManifestValidationError,
    fingerprint_system_under_test,
    parse_system_under_test,
)


def manifest_value() -> dict[str, object]:
    return {
        "name": "test-system",
        "workflow": "inbox_to_action",
        "runtime": "fixture",
        "runtime_version": "1",
        "provider": "fixture",
        "endpoint": "local-fixture",
        "model": "curated",
        "model_version": "test",
        "inference_policy": "deterministic-fixture-no-live-inference",
        "prompt_policy": "test-prompt",
        "memory_policy": "no-memory",
        "tool_policy": "inert-tools",
        "approval_policy": "confirm-actions",
        "context_snapshot": "synthetic",
        "safeguards": ["inert-tools", "context-labels"],
    }


class ManifestTests(unittest.TestCase):
    def test_fingerprint_is_canonical_and_policy_sensitive(self) -> None:
        first = manifest_value()
        second = manifest_value()
        second["safeguards"] = list(reversed(second["safeguards"]))  # type: ignore[arg-type]
        first_system = parse_system_under_test(first)
        second_system = parse_system_under_test(second)
        self.assertEqual(
            fingerprint_system_under_test(first_system),
            fingerprint_system_under_test(second_system),
        )
        changed = manifest_value()
        changed["approval_policy"] = "confirm-every-tool"
        self.assertNotEqual(
            fingerprint_system_under_test(first_system),
            fingerprint_system_under_test(parse_system_under_test(changed)),
        )

    def test_rejects_missing_unknown_and_secret_like_values(self) -> None:
        missing = manifest_value()
        del missing["runtime_version"]
        with self.assertRaisesRegex(ManifestValidationError, "missing required keys"):
            parse_system_under_test(missing)
        unknown = manifest_value()
        unknown["extra"] = "value"
        with self.assertRaisesRegex(ManifestValidationError, "unknown keys"):
            parse_system_under_test(unknown)
        secret = manifest_value()
        secret["context_snapshot"] = "api_key=do-not-store-this-value"
        with self.assertRaisesRegex(ManifestValidationError, "credential or secret"):
            parse_system_under_test(secret)
        placeholder = manifest_value()
        placeholder["model"] = "replace-with-pinned-model-id"
        with self.assertRaisesRegex(ManifestValidationError, "example placeholder"):
            parse_system_under_test(placeholder)


if __name__ == "__main__":
    unittest.main()
