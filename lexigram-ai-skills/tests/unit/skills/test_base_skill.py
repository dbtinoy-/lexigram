"""Tests for BaseSkill, FunctionSkill, and ToolSkillAdapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.ai.skills import SkillDefinition, SkillResult
from lexigram.result import Ok

from lexigram.ai.skills.base import AbstractSkill, FunctionSkill, ToolSkillAdapter


class _SimpleSkill(AbstractSkill):
    """Minimal concrete BaseSkill for testing validation path."""

    _defn = SkillDefinition(
        name="simple",
        description="Simple test skill.",
        parameters_schema={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
            },
            "required": ["name"],
        },
        category="test",
    )

    @property
    def definition(self) -> SkillDefinition:
        return self._defn

    async def execute(self, **kwargs):
        return Ok(SkillResult(skill_name="simple", success=True, output=kwargs))


class TestBaseSkill:
    """Tests for BaseSkill.validate()."""

    def test_validate_passes_with_valid_params(self) -> None:
        skill = _SimpleSkill()
        errors = skill.validate({"name": "Alice", "age": 30})
        assert errors == []

    def test_validate_fails_missing_required(self) -> None:
        skill = _SimpleSkill()
        errors = skill.validate({})
        assert any("name" in e for e in errors)

    def test_validate_fails_wrong_type(self) -> None:
        skill = _SimpleSkill()
        errors = skill.validate({"name": "Alice", "age": "not-an-int"})
        assert any("age" in e for e in errors)

    def test_definition_properties(self) -> None:
        skill = _SimpleSkill()
        assert skill.definition.name == "simple"
        assert skill.definition.category == "test"


class TestFunctionSkill:
    """Tests for FunctionSkill created from an async function."""

    @pytest.mark.asyncio
    async def test_execute_calls_wrapped_function(self) -> None:
        async def greet(name: str) -> dict:
            return {"greeting": f"Hello, {name}!"}

        defn = SkillDefinition(
            name="greet",
            description="Greet a user.",
            parameters_schema={
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
            category="test",
        )
        skill = FunctionSkill(fn=greet, definition=defn, param_names=["name"])
        result = await skill.execute(name="Alice")

        assert result.is_ok()
        assert result.unwrap().output == {"greeting": "Hello, Alice!"}

    @pytest.mark.asyncio
    async def test_execute_wraps_dict_output(self) -> None:
        async def noop(**kwargs) -> dict:
            return {"ok": True}

        defn = SkillDefinition(
            name="noop",
            description="No-op.",
            parameters_schema={"type": "object", "properties": {}, "required": []},
            category="test",
        )
        skill = FunctionSkill(fn=noop, definition=defn, param_names=[])
        result = await skill.execute()

        assert result.is_ok()
        assert result.unwrap().skill_name == "noop"


class TestToolSkillAdapter:
    """Tests for ToolSkillAdapter wrapping a ToolProtocol."""

    def _make_tool(self) -> MagicMock:
        tool = MagicMock()
        tool.name = "my_tool"
        tool.description = "A mock tool."
        tool.parameters = {"type": "object", "properties": {}, "required": []}
        tool.execute = AsyncMock(return_value={"result": 42})
        return tool

    @pytest.mark.asyncio
    async def test_execute_delegates_to_tool(self) -> None:
        tool = self._make_tool()
        adapter = ToolSkillAdapter(tool)
        result = await adapter.execute(x=1)

        assert result.is_ok()
        tool.execute.assert_awaited_once_with(x=1)

    def test_definition_reflects_tool_name(self) -> None:
        tool = self._make_tool()
        adapter = ToolSkillAdapter(tool)
        assert adapter.definition.name == "my_tool"
        assert adapter.definition.category == "tool"

    def test_validate_always_returns_empty(self) -> None:
        tool = self._make_tool()
        adapter = ToolSkillAdapter(tool)
        assert adapter.validate({}) == []
