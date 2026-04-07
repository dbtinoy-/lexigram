"""Unit tests for lexigram-ai-prompt types."""

import pytest

from lexigram.ai.prompt.variables.types import PromptContext, PromptVariable


class TestPromptVariable:
    """Tests for PromptVariable dataclass."""

    def test_prompt_variable_creation(self) -> None:
        """Test PromptVariable creation with required fields."""
        var = PromptVariable(name="username")

        assert var.name == "username"
        assert var.type == str
        assert var.required is False
        assert var.default is None
        assert var.description == ""
        assert var.max_length is None
        assert var.allowed_values is None

    def test_prompt_variable_with_all_fields(self) -> None:
        """Test PromptVariable creation with all fields."""
        var = PromptVariable(
            name="age",
            type=int,
            required=True,
            default=18,
            description="User's age",
            max_length=3,
            allowed_values=[18, 21, 25],
        )

        assert var.name == "age"
        assert var.type == int
        assert var.required is True
        assert var.default == 18
        assert var.description == "User's age"
        assert var.max_length == 3
        assert var.allowed_values == [18, 21, 25]

    def test_prompt_variable_defaults(self) -> None:
        """Test PromptVariable default values."""
        var = PromptVariable(name="test")

        assert var.type == str
        assert var.required is False
        assert var.default is None
        assert var.description == ""


class TestPromptContext:
    """Tests for PromptContext dataclass."""

    def test_prompt_context_creation(self) -> None:
        """Test PromptContext creation."""
        ctx = PromptContext()

        assert ctx.variables == {}
        assert ctx.metadata == {}

    def test_prompt_context_with_data(self) -> None:
        """Test PromptContext with data."""
        ctx = PromptContext(
            variables={"name": "John", "age": 30},
            metadata={"source": "test"},
        )

        assert ctx.variables == {"name": "John", "age": 30}
        assert ctx.metadata == {"source": "test"}

    def test_prompt_context_from_kwargs(self) -> None:
        """Test PromptContext creation from kwargs."""
        ctx = PromptContext.from_kwargs(name="Alice", age=25)

        assert ctx.variables == {"name": "Alice", "age": 25}
        assert ctx.metadata == {}

    def test_prompt_context_from_kwargs_empty(self) -> None:
        """Test PromptContext creation from empty kwargs."""
        ctx = PromptContext.from_kwargs()

        assert ctx.variables == {}


class TestPromptTypesExports:
    """Tests for prompt types module exports."""

    def test_all_exports(self) -> None:
        """Test that all types are properly exported."""
        from lexigram.ai.prompt.variables import types

        expected = ["PromptContext", "PromptVariable"]
        for name in expected:
            assert hasattr(types, name)
