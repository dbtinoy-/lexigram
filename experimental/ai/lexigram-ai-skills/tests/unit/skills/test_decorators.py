"""Tests for @skill and @skill_param decorators."""

from __future__ import annotations

import pytest

from lexigram.ai.skills.base import FunctionSkill
from lexigram.ai.skills.decorators import skill, skill_param


class TestSkillDecorator:
    """Tests for the @skill decorator."""

    def test_returns_function_skill(self) -> None:
        @skill(name="add", description="Add two numbers.", category="math")
        @skill_param("a", type="integer", description="First operand.", required=True)
        @skill_param("b", type="integer", description="Second operand.", required=True)
        async def add(a: int, b: int) -> dict:
            return {"sum": a + b}

        assert isinstance(add, FunctionSkill)
        assert add.definition.name == "add"

    def test_definition_has_correct_description(self) -> None:
        @skill(name="greet", description="Greet user.")
        @skill_param("name", type="string", description="Name.", required=True)
        async def greet(name: str):
            ...

        assert greet.definition.description == "Greet user."

    def test_parameters_schema_includes_declared_params(self) -> None:
        @skill(name="op", description="Op.")
        @skill_param("x", type="number", description="X.", required=True)
        @skill_param("y", type="number", description="Y.", required=False)
        async def op(x: float, y: float = 0.0):
            ...

        schema = op.definition.parameters_schema
        assert "x" in schema["properties"]
        assert "y" in schema["properties"]
        assert "x" in schema["required"]
        assert "y" not in schema["required"]

    def test_category_default_is_custom(self) -> None:
        @skill(name="noop", description="N.")
        async def noop():
            ...

        assert noop.definition.category == "general"

    def test_required_permissions_set_on_definition(self) -> None:
        @skill(
            name="restricted",
            description="Restricted.",
            permissions=["admin", "superuser"],
        )
        async def restricted():
            ...

        assert set(restricted.definition.permissions) == {"admin", "superuser"}

    @pytest.mark.asyncio
    async def test_decorated_skill_is_callable_via_execute(self) -> None:
        @skill(name="double", description="Double.")
        @skill_param("n", type="integer", description="Number.", required=True)
        async def double(n: int) -> dict:
            return {"result": n * 2}

        result = await double.execute(n=5)
        assert result.is_ok()
        assert result.unwrap().output == {"result": 10}


class TestSkillParamDecorator:
    """Tests for the @skill_param decorator."""

    def test_accumulates_multiple_params(self) -> None:
        @skill_param("a", type="string", description="A.", required=True)
        @skill_param("b", type="integer", description="B.", required=False)
        async def fn():
            ...

        # _skill_params contains params in declaration order
        params = fn._skill_params  # type: ignore[attr-defined]
        names = [p["name"] for p in params]
        assert "a" in names
        assert "b" in names

    def test_enum_included_in_schema(self) -> None:
        @skill(name="colour", description="Pick colour.")
        @skill_param("c", type="string", description="Colour.", enum=["red", "green", "blue"])
        async def colour(c: str):
            ...

        prop = colour.definition.parameters_schema["properties"]["c"]
        assert prop.get("enum") == ["red", "green", "blue"]

    def test_default_included_in_schema(self) -> None:
        @skill(name="timeout", description="Timeout.")
        @skill_param("t", type="number", description="Timeout.", default=30.0)
        async def timeout_fn(t: float):
            ...

        prop = timeout_fn.definition.parameters_schema["properties"]["t"]
        assert prop.get("default") == 30.0
