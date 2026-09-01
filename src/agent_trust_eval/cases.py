"""Strict JSON suite loading and validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import EvalCase, EvalSuite, Expectations


KNOWN_CATEGORIES = frozenset(
    {
        "ambiguity",
        "prompt_injection",
        "tool_use_restraint",
        "approval_boundaries",
        "contextual_integrity",
        "memory_boundaries",
        "provenance",
        "secret_handling",
        "unsafe_retrieval",
        "refusal_consistency",
    }
)
KNOWN_SCENARIO_TYPES = frozenset({"benign", "adversarial"})
KNOWN_PERMISSION_LEVELS = frozenset(
    {
        "read_only",
        "draft_only",
        "confirm_before_action",
        "reversible_action",
        "consequential_action",
    }
)


class CaseValidationError(ValueError):
    """Raised when an evaluation suite does not match the public schema."""


def _object(value: Any, location: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CaseValidationError(f"{location} must be a JSON object")
    return value


def _keys(value: dict[str, Any], *, required: set[str], allowed: set[str], location: str) -> None:
    missing = sorted(required - value.keys())
    unknown = sorted(value.keys() - allowed)
    if missing:
        raise CaseValidationError(f"{location} is missing required keys: {', '.join(missing)}")
    if unknown:
        raise CaseValidationError(f"{location} has unknown keys: {', '.join(unknown)}")


def _text(value: Any, location: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise CaseValidationError(f"{location} must be a non-empty string")
    return value


def _text_tuple(value: Any, location: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise CaseValidationError(f"{location} must be an array of strings")
    return tuple(_text(item, f"{location}[{index}]") for index, item in enumerate(value))


def _expectations(value: Any, location: str) -> Expectations:
    data = _object(value, location)
    allowed = {
        "required_phrases",
        "required_any",
        "forbidden_phrases",
        "allowed_tools",
        "required_tools",
    }
    _keys(data, required=set(), allowed=allowed, location=location)
    normalized = {key: _text_tuple(data.get(key, []), f"{location}.{key}") for key in allowed}
    if not any(normalized.values()):
        raise CaseValidationError(f"{location} must declare at least one grading rule")
    required_tools = set(normalized["required_tools"])
    allowed_tools = set(normalized["allowed_tools"])
    if not required_tools.issubset(allowed_tools):
        raise CaseValidationError(f"{location}.required_tools must also appear in allowed_tools")
    return Expectations(**normalized)


def _tools(value: Any, location: str) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, list):
        raise CaseValidationError(f"{location} must be an array")
    tools: list[dict[str, Any]] = []
    names: set[str] = set()
    for index, raw in enumerate(value):
        item_location = f"{location}[{index}]"
        tool = _object(raw, item_location)
        _keys(tool, required={"type", "function"}, allowed={"type", "function"}, location=item_location)
        if tool["type"] != "function":
            raise CaseValidationError(f"{item_location}.type must be 'function'")
        function = _object(tool["function"], f"{item_location}.function")
        _keys(
            function,
            required={"name", "description", "parameters"},
            allowed={"name", "description", "parameters"},
            location=f"{item_location}.function",
        )
        name = _text(function["name"], f"{item_location}.function.name")
        _text(function["description"], f"{item_location}.function.description")
        parameters = _object(function["parameters"], f"{item_location}.function.parameters")
        if name in names:
            raise CaseValidationError(f"{location} contains duplicate tool name: {name}")
        names.add(name)
        tools.append({"type": "function", "function": {**function, "parameters": parameters}})
    return tuple(tools)


def load_suite(path: Path) -> EvalSuite:
    """Load and validate a v2 evaluation suite from *path*."""

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CaseValidationError(f"suite file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CaseValidationError(f"invalid JSON in {path}: line {exc.lineno}, column {exc.colno}") from exc

    root = _object(raw, str(path))
    _keys(
        root,
        required={"schema_version", "name", "description", "workflow", "version", "cases"},
        allowed={"schema_version", "name", "description", "workflow", "version", "cases"},
        location=str(path),
    )
    if root["schema_version"] != "2.0":
        raise CaseValidationError(
            f"{path}.schema_version must be '2.0'; v1 suites require migration"
        )
    name = _text(root["name"], f"{path}.name")
    description = _text(root["description"], f"{path}.description")
    workflow = _text(root["workflow"], f"{path}.workflow")
    version = _text(root["version"], f"{path}.version")
    if not isinstance(root["cases"], list) or not root["cases"]:
        raise CaseValidationError(f"{path}.cases must be a non-empty array")

    cases: list[EvalCase] = []
    ids: set[str] = set()
    required = {
        "id",
        "title",
        "scenario_type",
        "risk_category",
        "permission_level",
        "critical",
        "tags",
        "description",
        "system_prompt",
        "prompt",
        "context",
        "tools",
        "expectations",
    }
    for index, raw_case in enumerate(root["cases"]):
        location = f"{path}.cases[{index}]"
        data = _object(raw_case, location)
        _keys(data, required=required, allowed=required, location=location)
        case_id = _text(data["id"], f"{location}.id")
        if case_id in ids:
            raise CaseValidationError(f"{location}.id is duplicated: {case_id}")
        ids.add(case_id)
        scenario_type = _text(data["scenario_type"], f"{location}.scenario_type")
        if scenario_type not in KNOWN_SCENARIO_TYPES:
            raise CaseValidationError(
                f"{location}.scenario_type must be one of: {', '.join(sorted(KNOWN_SCENARIO_TYPES))}"
            )
        risk_category = _text(data["risk_category"], f"{location}.risk_category")
        if risk_category not in KNOWN_CATEGORIES:
            raise CaseValidationError(
                f"{location}.risk_category must be one of: {', '.join(sorted(KNOWN_CATEGORIES))}"
            )
        permission_level = _text(data["permission_level"], f"{location}.permission_level")
        if permission_level not in KNOWN_PERMISSION_LEVELS:
            raise CaseValidationError(
                f"{location}.permission_level must be one of: "
                f"{', '.join(sorted(KNOWN_PERMISSION_LEVELS))}"
            )
        critical = data["critical"]
        if not isinstance(critical, bool):
            raise CaseValidationError(f"{location}.critical must be a boolean")
        tags = _text_tuple(data["tags"], f"{location}.tags")
        if len(tags) != len(set(tags)):
            raise CaseValidationError(f"{location}.tags must not contain duplicates")
        tools = _tools(data["tools"], f"{location}.tools")
        expectations = _expectations(data["expectations"], f"{location}.expectations")
        declared_tools = {tool["function"]["name"] for tool in tools}
        undeclared_tools = sorted(set(expectations.allowed_tools) - declared_tools)
        if undeclared_tools:
            raise CaseValidationError(
                f"{location}.expectations.allowed_tools references undeclared tools: {', '.join(undeclared_tools)}"
            )
        cases.append(
            EvalCase(
                id=case_id,
                title=_text(data["title"], f"{location}.title"),
                scenario_type=scenario_type,
                risk_category=risk_category,
                permission_level=permission_level,
                critical=critical,
                tags=tags,
                description=_text(data["description"], f"{location}.description"),
                system_prompt=_text(data["system_prompt"], f"{location}.system_prompt"),
                prompt=_text(data["prompt"], f"{location}.prompt"),
                context=_text_tuple(data["context"], f"{location}.context"),
                tools=tools,
                expectations=expectations,
            )
        )
    return EvalSuite(
        schema_version="2.0",
        name=name,
        description=description,
        workflow=workflow,
        version=version,
        cases=tuple(cases),
    )


def load_cases(path: Path) -> list[EvalCase]:
    """Compatibility helper returning only the ordered cases from a v2 suite."""

    return list(load_suite(path).cases)
