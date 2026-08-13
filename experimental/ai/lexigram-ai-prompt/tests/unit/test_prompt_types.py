"""Tests for prompt types module."""

from __future__ import annotations

import pytest
from lexigram.ai.prompt.variables.types import PromptVariable, PromptContext
from lexigram.ai.prompt.rendering.engine import RenderFormat


class TestPromptVariable:
    """Tests for PromptVariable dataclass."""

    def test_create_required_variable(self) -> None:
        var = PromptVariable(name="user_name", required=True)
        assert var.name == "user_name"
        assert var.type == str
        assert var.required is True
        assert var.default is None

    def test_create_optional_variable_with_default(self) -> None:
        var = PromptVariable(
            name="count",
            type=int,
            required=False,
            default=10,
            description="Number of items",
            max_length=100,
            allowed_values=[1, 2, 3],
        )
        assert var.name == "count"
        assert var.type == int
        assert var.required is False
        assert var.default == 10
        assert var.description == "Number of items"
        assert var.max_length == 100
        assert var.allowed_values == [1, 2, 3]

    def test_default_type_is_str(self) -> None:
        var = PromptVariable(name="test")
        assert var.type == str

    def test_default_required_is_false(self) -> None:
        var = PromptVariable(name="test")
        assert var.required is False

    def test_default_max_length_is_none(self) -> None:
        var = PromptVariable(name="test")
        assert var.max_length is None

    def test_default_allowed_values_is_none(self) -> None:
        var = PromptVariable(name="test")
        assert var.allowed_values is None


class TestPromptContext:
    """Tests for PromptContext dataclass."""

    def test_create_empty_context(self) -> None:
        ctx = PromptContext()
        assert ctx.variables == {}
        assert ctx.metadata == {}

    def test_create_with_variables(self) -> None:
        ctx = PromptContext(variables={"name": "Alice", "age": 30})
        assert ctx.variables == {"name": "Alice", "age": 30}
        assert ctx.metadata == {}

    def test_create_with_metadata(self) -> None:
        ctx = PromptContext(metadata={"source": "test"})
        assert ctx.variables == {}
        assert ctx.metadata == {"source": "test"}

    def test_create_with_both(self) -> None:
        ctx = PromptContext(
            variables={"key": "value"},
            metadata={"request_id": "123"},
        )
        assert ctx.variables == {"key": "value"}
        assert ctx.metadata == {"request_id": "123"}

    def test_from_kwargs(self) -> None:
        ctx = PromptContext.from_kwargs(name="Bob", count=5)
        assert ctx.variables == {"name": "Bob", "count": 5}

    def test_from_kwargs_empty(self) -> None:
        ctx = PromptContext.from_kwargs()
        assert ctx.variables == {}


class TestRenderFormat:
    """Tests for RenderFormat enum."""

    def test_f_string_value(self) -> None:
        assert RenderFormat.F_STRING.value == "f_string"

    def test_jinja2_value(self) -> None:
        assert RenderFormat.JINJA2.value == "jinja2"

    def test_dollar_value(self) -> None:
        assert RenderFormat.DOLLAR.value == "dollar"

    def test_simple_value(self) -> None:
        assert RenderFormat.SIMPLE.value == "simple"

    def test_all_formats_exist(self) -> None:
        formats = list(RenderFormat)
        assert len(formats) == 4
        assert RenderFormat.F_STRING in formats
        assert RenderFormat.JINJA2 in formats
        assert RenderFormat.DOLLAR in formats
        assert RenderFormat.SIMPLE in formats

    def test_is_str_enum(self) -> None:
        fmt = RenderFormat.JINJA2
        assert isinstance(fmt, str)
        assert str(fmt) == "jinja2"