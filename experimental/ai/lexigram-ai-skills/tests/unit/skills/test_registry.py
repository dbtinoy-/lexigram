"""Tests for SkillRegistry."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from lexigram.contracts.ai.skills import SkillDefinition

from lexigram.ai.skills.exceptions import SkillAlreadyRegisteredError
from lexigram.ai.skills.registry import SkillRegistry


class TestSkillRegistry:
    """Tests for SkillRegistry CRUD operations."""

    def test_register_and_get(self, echo_skill) -> None:
        reg = SkillRegistry()
        reg.register(echo_skill)
        retrieved = reg.get("echo")
        assert retrieved is echo_skill

    def test_get_unknown_returns_none(self) -> None:
        reg = SkillRegistry()
        assert reg.get("nonexistent") is None

    def test_register_duplicate_raises(self, echo_skill) -> None:
        reg = SkillRegistry()
        reg.register(echo_skill)
        with pytest.raises(SkillAlreadyRegisteredError):
            reg.register(echo_skill)

    def test_list_skills_returns_all(self, echo_skill, fail_skill) -> None:
        reg = SkillRegistry()
        reg.register(echo_skill)
        reg.register(fail_skill)
        names = [s.name for s in reg.list_skills()]
        assert "echo" in names
        assert "fail" in names

    def test_list_skills_filters_by_category(self, echo_skill, fail_skill) -> None:
        reg = SkillRegistry()
        reg.register(echo_skill)
        reg.register(fail_skill)
        test_only = reg.list_skills(category="test")
        for s in test_only:
            assert s.category == "test"

    def test_len_reflects_registered_count(self, echo_skill, fail_skill) -> None:
        reg = SkillRegistry()
        assert len(reg) == 0
        reg.register(echo_skill)
        assert len(reg) == 1
        reg.register(fail_skill)
        assert len(reg) == 2

    def test_contains_returns_true_for_registered(self, echo_skill) -> None:
        reg = SkillRegistry()
        reg.register(echo_skill)
        assert "echo" in reg

    def test_contains_returns_false_for_missing(self) -> None:
        reg = SkillRegistry()
        assert "ghost" not in reg

    def test_get_schemas_returns_openai_format(self, echo_skill) -> None:
        reg = SkillRegistry()
        reg.register(echo_skill)
        schemas = reg.get_schemas()
        assert len(schemas) == 1
        schema = schemas[0]
        assert schema["type"] == "function"
        assert "function" in schema
        assert schema["function"]["name"] == "echo"

    def test_register_tool_wraps_as_adapter(self) -> None:
        tool = MagicMock()
        tool.name = "my_tool"
        tool.description = "A tool."
        tool.parameters = {"type": "object", "properties": {}, "required": []}

        reg = SkillRegistry()
        reg.register_tool(tool)
        skill = reg.get("my_tool")
        assert skill is not None
        assert skill.definition.name == "my_tool"
