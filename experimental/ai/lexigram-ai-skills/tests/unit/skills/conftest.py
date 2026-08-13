"""Shared pytest fixtures for the skills unit test suite."""

from __future__ import annotations

import pytest

from lexigram.contracts.ai.skills import SkillDefinition, SkillResult
from lexigram.result import Ok

from lexigram.ai.skills.base import AbstractSkill
from lexigram.ai.skills.registry import SkillRegistry


class _EchoSkill(AbstractSkill):
    """Test skill that echoes its input parameters."""

    def __init__(self, name: str = "echo", category: str = "test") -> None:
        self._name = name
        self._category = category

    @property
    def definition(self) -> SkillDefinition:
        return SkillDefinition(
            name=self._name,
            description="Echo skill for tests.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                },
                "required": [],
            },
            category=self._category,
        )

    async def execute(self, **kwargs):
        return Ok(
            SkillResult(
                skill_name=self._name,
                success=True,
                output=dict(kwargs),
            )
        )


class _FailSkill(AbstractSkill):
    """Test skill that always returns an error result."""

    @property
    def definition(self) -> SkillDefinition:
        return SkillDefinition(
            name="fail",
            description="Always fails.",
            parameters_schema={"type": "object", "properties": {}, "required": []},
            category="test",
        )

    async def execute(self, **kwargs):
        from lexigram.result import Err
        from lexigram.ai.skills.exceptions import SkillExecutionError

        return Err(SkillExecutionError("intentional failure"))


@pytest.fixture
def echo_skill() -> _EchoSkill:
    """Return a fresh EchoSkill instance."""
    return _EchoSkill()


@pytest.fixture
def fail_skill() -> _FailSkill:
    """Return a fresh FailSkill instance."""
    return _FailSkill()


@pytest.fixture
def registry() -> SkillRegistry:
    """Return an empty SkillRegistry."""
    return SkillRegistry()


@pytest.fixture
def populated_registry(echo_skill: _EchoSkill) -> SkillRegistry:
    """Return a SkillRegistry pre-loaded with the echo skill."""
    reg = SkillRegistry()
    reg.register(echo_skill)
    return reg
