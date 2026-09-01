"""Typed data exchanged by loaders, providers, graders, and reporters."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolCall:
    """A normalized tool request emitted by a model endpoint."""

    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderResponse:
    """Provider-independent model response."""

    text: str
    tool_calls: tuple[ToolCall, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass(frozen=True)
class Expectations:
    """Declarative v1 grading rules for one evaluation case."""

    required_phrases: tuple[str, ...] = ()
    required_any: tuple[str, ...] = ()
    forbidden_phrases: tuple[str, ...] = ()
    allowed_tools: tuple[str, ...] = ()
    required_tools: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvalCase:
    """One synthetic trust probe."""

    id: str
    title: str
    scenario_type: str
    risk_category: str
    permission_level: str
    critical: bool
    tags: tuple[str, ...]
    description: str
    system_prompt: str
    prompt: str
    context: tuple[str, ...]
    tools: tuple[dict[str, Any], ...]
    expectations: Expectations

    @property
    def category(self) -> str:
        """Compatibility alias for the v1 category name."""

        return self.risk_category


@dataclass(frozen=True)
class EvalSuite:
    """Versioned metadata and ordered cases for one workflow suite."""

    schema_version: str
    name: str
    description: str
    workflow: str
    version: str
    cases: tuple[EvalCase, ...]


@dataclass(frozen=True)
class CheckResult:
    """Outcome of one transparent grading check."""

    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class CaseResult:
    """Complete result for one evaluation case."""

    case: EvalCase
    response: ProviderResponse
    checks: tuple[CheckResult, ...]

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)
