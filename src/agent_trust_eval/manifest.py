"""Pinned system-under-test manifests and stable configuration fingerprints.

V0.1 treats the complete agent assembly—not the model alone—as the evaluated
unit. Stage one implements strict loading, secret rejection, canonicalization,
and SHA-256 fingerprinting behind this module boundary.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import re


class ManifestValidationError(ValueError):
    """Raised when a system-under-test manifest is incomplete or unsafe."""


@dataclass(frozen=True)
class SystemUnderTest:
    """Non-secret identity and policy metadata for one evaluated assembly."""

    name: str
    workflow: str
    runtime: str
    runtime_version: str
    provider: str
    endpoint: str
    model: str
    model_version: str
    inference_policy: str
    prompt_policy: str
    memory_policy: str
    tool_policy: str
    approval_policy: str
    context_snapshot: str
    safeguards: tuple[str, ...]


def parse_system_under_test(value: object) -> SystemUnderTest:
    """Validate and normalize a system-under-test JSON object."""

    if not isinstance(value, dict):
        raise ManifestValidationError("system_under_test must be a JSON object")
    fields = {
        "name",
        "workflow",
        "runtime",
        "runtime_version",
        "provider",
        "endpoint",
        "model",
        "model_version",
        "inference_policy",
        "prompt_policy",
        "memory_policy",
        "tool_policy",
        "approval_policy",
        "context_snapshot",
        "safeguards",
    }
    missing = sorted(fields - value.keys())
    unknown = sorted(value.keys() - fields)
    if missing:
        raise ManifestValidationError(
            f"system_under_test is missing required keys: {', '.join(missing)}"
        )
    if unknown:
        raise ManifestValidationError(
            f"system_under_test has unknown keys: {', '.join(unknown)}"
        )

    normalized: dict[str, str] = {}
    for key in sorted(fields - {"safeguards"}):
        item = value[key]
        if not isinstance(item, str) or not item.strip():
            raise ManifestValidationError(f"system_under_test.{key} must be a non-empty string")
        text = item.strip()
        if text.casefold().startswith("replace-with-"):
            raise ManifestValidationError(
                f"system_under_test.{key} still contains an example placeholder"
            )
        if _looks_secret(text):
            raise ManifestValidationError(
                f"system_under_test.{key} appears to contain a credential or secret"
            )
        normalized[key] = text

    raw_safeguards = value["safeguards"]
    if not isinstance(raw_safeguards, list):
        raise ManifestValidationError("system_under_test.safeguards must be an array of strings")
    safeguards: list[str] = []
    for index, item in enumerate(raw_safeguards):
        if not isinstance(item, str) or not item.strip():
            raise ManifestValidationError(
                f"system_under_test.safeguards[{index}] must be a non-empty string"
            )
        text = item.strip()
        if text.casefold().startswith("replace-with-"):
            raise ManifestValidationError(
                f"system_under_test.safeguards[{index}] still contains an example placeholder"
            )
        if _looks_secret(text):
            raise ManifestValidationError(
                f"system_under_test.safeguards[{index}] appears to contain a credential or secret"
            )
        safeguards.append(text)
    if len(safeguards) != len(set(safeguards)):
        raise ManifestValidationError("system_under_test.safeguards must not contain duplicates")
    return SystemUnderTest(**normalized, safeguards=tuple(sorted(safeguards)))


def fingerprint_system_under_test(system: SystemUnderTest) -> str:
    """Return the stable SHA-256 fingerprint for *system*."""

    canonical = json.dumps(
        system_under_test_dict(system),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"sha256:{sha256(canonical).hexdigest()}"


def system_under_test_dict(system: SystemUnderTest) -> dict[str, object]:
    """Return the stable public JSON representation of *system*."""

    value = asdict(system)
    value["safeguards"] = list(system.safeguards)
    return value


_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----", re.IGNORECASE),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b", re.IGNORECASE),
    re.compile(r"\bapi[_ -]?key\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"\bbearer\s+[A-Za-z0-9._-]{12,}", re.IGNORECASE),
)


def _looks_secret(value: str) -> bool:
    return any(pattern.search(value) for pattern in _SECRET_PATTERNS)
