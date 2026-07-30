"""Tests for PromptVariable and PromptContext."""

from __future__ import annotations

import pytest

from lexigram.ai.prompt.exceptions import PromptRenderError, PromptValidationError
from lexigram.ai.prompt.variables.types import PromptContext, PromptVariable
from lexigram.ai.prompt.variables.validators import resolve_variables, validate_variable

# ---------------------------------------------------------------------------
# PromptVariable
# ---------------------------------------------------------------------------


def test_prompt_variable_defaults() -> None:
    v = PromptVariable("name")
    assert v.name == "name"
    assert v.type is str
    assert v.required is False
    assert v.default is None
    assert v.max_length is None
    assert v.allowed_values is None


def test_prompt_variable_all_fields() -> None:
    v = PromptVariable(
        "role",
        type=str,
        required=True,
        default="admin",
        description="User role",
        max_length=50,
        allowed_values=["admin", "user"],
    )
    assert v.required is True
    assert v.max_length == 50
    assert v.allowed_values == ["admin", "user"]


# ---------------------------------------------------------------------------
# validate_variable
# ---------------------------------------------------------------------------


def test_validate_variable_type_ok() -> None:
    v = PromptVariable("age", type=int)
    validate_variable(v, 42)  # should not raise


def test_validate_variable_type_error() -> None:
    v = PromptVariable("age", type=int)
    with pytest.raises(PromptValidationError, match="expected int, got str"):
        validate_variable(v, "not-an-int")


def test_validate_variable_max_length_ok() -> None:
    v = PromptVariable("msg", max_length=10)
    validate_variable(v, "hello")


def test_validate_variable_max_length_exceeded() -> None:
    v = PromptVariable("msg", max_length=5)
    with pytest.raises(PromptValidationError, match="exceeds max_length=5"):
        validate_variable(v, "toolongstring")


def test_validate_variable_global_max_length_ok() -> None:
    v = PromptVariable("msg")
    validate_variable(v, "hello", max_variable_length=10)


def test_validate_variable_global_max_length_exceeded() -> None:
    v = PromptVariable("msg")
    with pytest.raises(PromptValidationError, match="exceeds max_variable_length=5"):
        validate_variable(v, "toolongstring", max_variable_length=5)


def test_validate_variable_global_max_length_unlimited_by_default() -> None:
    v = PromptVariable("msg")
    validate_variable(v, "x" * 100_000)  # default 0 = unlimited


def test_validate_variable_allowed_values_ok() -> None:
    v = PromptVariable("color", allowed_values=["red", "blue"])
    validate_variable(v, "red")


def test_validate_variable_allowed_values_rejected() -> None:
    v = PromptVariable("color", allowed_values=["red", "blue"])
    with pytest.raises(PromptValidationError, match="not in allowed_values"):
        validate_variable(v, "green")


# ---------------------------------------------------------------------------
# resolve_variables
# ---------------------------------------------------------------------------


def test_resolve_uses_supplied_value() -> None:
    declared = [PromptVariable("name", required=True)]
    result = resolve_variables(declared, {"name": "Alice"})
    assert result["name"] == "Alice"


def test_resolve_uses_default() -> None:
    declared = [PromptVariable("role", default="user")]
    result = resolve_variables(declared, {})
    assert result["role"] == "user"


def test_resolve_missing_required_raises() -> None:
    declared = [PromptVariable("company", required=True)]
    with pytest.raises(PromptRenderError, match="Required variable 'company'"):
        resolve_variables(declared, {})


def test_resolve_passes_through_extra_kwargs() -> None:
    declared = [PromptVariable("name")]
    result = resolve_variables(declared, {"name": "Bob", "extra": "value"})
    assert result["extra"] == "value"


def test_resolve_enforces_global_max_length() -> None:
    declared = [PromptVariable("name", required=True)]
    with pytest.raises(PromptValidationError, match="exceeds max_variable_length=3"):
        resolve_variables(declared, {"name": "toolong"}, max_variable_length=3)


def test_resolve_permissive_passthrough_enforces_global_max_length() -> None:
    declared = [PromptVariable("name")]
    with pytest.raises(PromptValidationError, match="Variable 'extra'"):
        resolve_variables(
            declared,
            {"name": "ok", "extra": "x" * 100},
            max_variable_length=5,
        )


def test_resolve_permissive_passthrough_under_global_max_length() -> None:
    declared = [PromptVariable("name")]
    result = resolve_variables(
        declared, {"name": "ok", "extra": "short"}, max_variable_length=10
    )
    assert result["extra"] == "short"


def test_resolve_validates_type() -> None:
    declared = [PromptVariable("count", type=int)]
    with pytest.raises(PromptValidationError):
        resolve_variables(declared, {"count": "not-int"})


# ---------------------------------------------------------------------------
# PromptContext
# ---------------------------------------------------------------------------


def test_prompt_context_from_kwargs() -> None:
    ctx = PromptContext.from_kwargs(topic="AI", tone="formal")
    assert ctx.variables == {"topic": "AI", "tone": "formal"}
    assert ctx.metadata == {}


def test_prompt_context_defaults() -> None:
    ctx = PromptContext()
    assert ctx.variables == {}
    assert ctx.metadata == {}
