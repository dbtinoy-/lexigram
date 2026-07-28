"""@skill and @skill_param decorators for function-based skill definitions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.ai.skills.base import FunctionSkill
from lexigram.contracts.ai.skills import SkillDefinition

if TYPE_CHECKING:
    from collections.abc import Callable

# Sentinel attribute placed on decorated functions by @skill_param
_SKILL_PARAMS_ATTR = "_skill_params"


def skill_param(
    name: str,
    *,
    type: str = "string",
    description: str = "",
    required: bool = True,
    default: Any = None,
    enum: list[Any] | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    max_length: int | None = None,
) -> Callable:
    """Declare a parameter on a skill function.

    Must be applied before ``@skill``.  Multiple ``@skill_param`` decorators
    are accumulated in declaration order.

    Args:
        name: Parameter name.
        type: JSON Schema type (e.g. ``"string"``, ``"integer"``, ``"boolean"``).
        description: Human-readable description.
        required: Whether the parameter is required.
        default: Default value when not supplied.
        enum: Restricted set of allowed values.
        min_value: Numeric minimum.
        max_value: Numeric maximum.
        max_length: String maximum length.

    Returns:
        Decorator that annotates the function with parameter metadata.
    """

    def decorator(fn: Callable) -> Callable:
        params: list[dict[str, Any]] = getattr(fn, _SKILL_PARAMS_ATTR, [])
        params = [
            {
                "name": name,
                "type": type,
                "description": description,
                "required": required,
                "default": default,
                "enum": enum,
                "min_value": min_value,
                "max_value": max_value,
                "max_length": max_length,
            },
            *params,  # prepend so @skill_param nearest to def comes first
        ]
        setattr(fn, _SKILL_PARAMS_ATTR, params)
        return fn

    return decorator


def skill(
    name: str,
    description: str,
    *,
    category: str = "general",
    cacheable: bool = False,
    max_retries: int = 0,
    timeout_seconds: float = 30.0,
    requires_confirmation: bool = False,
    permissions: list[str] | None = None,
) -> Callable:
    """Convert an async function into a :class:`FunctionSkill`.

    Args:
        name: Unique skill name.
        description: What the skill does.
        category: Logical grouping for the skill.
        cacheable: Whether results can be cached.
        max_retries: Retry attempts on failure (0 = no retry).
        timeout_seconds: Execution timeout.
        requires_confirmation: If True, consumers may prompt for confirmation.
        permissions: Required permission strings.

    Returns:
        Decorator that wraps the function as a FunctionSkill.
    """

    def decorator(fn: Callable) -> FunctionSkill:
        raw_params: list[dict[str, Any]] = getattr(fn, _SKILL_PARAMS_ATTR, [])
        param_names = [p["name"] for p in raw_params]
        parameters_schema = _build_parameters_schema(raw_params)

        defn = SkillDefinition(
            name=name,
            description=description,
            parameters_schema=parameters_schema,
            category=category,
            cacheable=cacheable,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
            requires_confirmation=requires_confirmation,
            permissions=permissions or [],
        )
        return FunctionSkill(fn=fn, definition=defn, param_names=param_names)

    return decorator


def _build_parameters_schema(params: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a JSON Schema ``object`` from collected @skill_param metadata.

    Args:
        params: List of parameter descriptor dicts from ``@skill_param``.

    Returns:
        JSON Schema dict describing the parameters object.
    """
    properties: dict[str, Any] = {}
    required: list[str] = []

    for p in params:
        prop: dict[str, Any] = {"type": p["type"], "description": p["description"]}
        if p["enum"] is not None:
            prop["enum"] = p["enum"]
        if p["default"] is not None:
            prop["default"] = p["default"]
        if p["min_value"] is not None:
            prop["minimum"] = p["min_value"]
        if p["max_value"] is not None:
            prop["maximum"] = p["max_value"]
        if p["max_length"] is not None:
            prop["maxLength"] = p["max_length"]
        properties[p["name"]] = prop
        if p["required"]:
            required.append(p["name"])

    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


__all__ = ["skill", "skill_param"]
