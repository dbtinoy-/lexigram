"""Tests for SkillExecutor."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.ai.skills import SkillDefinition, SkillResult
from lexigram.result import Ok

from lexigram.ai.skills.base import AbstractSkill

BaseSkill = AbstractSkill
from lexigram.ai.skills.caching.skill_cache import SkillResultCache
from lexigram.ai.skills.exceptions import (
    SkillNotFoundError,
    SkillPermissionDeniedError,
    SkillValidationError,
)
from lexigram.ai.skills.executor import SkillExecutor
from lexigram.ai.skills.permissions.permission_checker import PermissionChecker
from lexigram.ai.skills.registry import SkillRegistry


class _RequiredSkill(AbstractSkill):
    """Skill that requires a 'message' string parameter."""

    @property
    def definition(self) -> SkillDefinition:
        return SkillDefinition(
            name="required_skill",
            description="Needs message.",
            parameters_schema={
                "type": "object",
                "properties": {"message": {"type": "string"}},
                "required": ["message"],
            },
            category="test",
        )

    async def execute(self, **kwargs):
        return Ok(SkillResult(skill_name="required_skill", success=True, output=kwargs))


class _PermSkill(AbstractSkill):
    """Skill that requires 'admin' permission."""

    @property
    def definition(self) -> SkillDefinition:
        return SkillDefinition(
            name="perm_skill",
            description="Admin only.",
            parameters_schema={"type": "object", "properties": {}, "required": []},
            category="admin",
            permissions=["admin"],
        )

    async def execute(self, **kwargs):
        return Ok(SkillResult(skill_name="perm_skill", success=True, output={}))


class TestSkillExecutor:
    """Tests for SkillExecutor full execution lifecycle."""

    @pytest.fixture
    def ex(self, populated_registry):
        return SkillExecutor(registry=populated_registry)

    @pytest.mark.asyncio
    async def test_execute_known_skill_returns_ok(self, ex) -> None:
        result = await ex.execute("echo", {"message": "hi"})
        assert result.is_ok()
        assert result.unwrap().skill_name == "echo"

    @pytest.mark.asyncio
    async def test_execute_unknown_skill_returns_err(self, populated_registry) -> None:
        ex = SkillExecutor(registry=populated_registry)
        result = await ex.execute("unknown_skill", {})
        assert result.is_err()
        assert isinstance(result.unwrap_err(), SkillNotFoundError)

    @pytest.mark.asyncio
    async def test_validation_error_on_missing_required(self) -> None:
        reg = SkillRegistry()
        reg.register(_RequiredSkill())
        ex = SkillExecutor(registry=reg)
        result = await ex.execute("required_skill", {})
        assert result.is_err()
        assert isinstance(result.unwrap_err(), SkillValidationError)

    @pytest.mark.asyncio
    async def test_permission_denied_without_grant(self) -> None:
        reg = SkillRegistry()
        reg.register(_PermSkill())
        checker = PermissionChecker()
        ex = SkillExecutor(registry=reg, permission_checker=checker)
        result = await ex.execute("perm_skill", {}, user_id="user1")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), SkillPermissionDeniedError)

    @pytest.mark.asyncio
    async def test_permission_granted_allows_execution(self) -> None:
        reg = SkillRegistry()
        reg.register(_PermSkill())
        checker = PermissionChecker()
        checker.grant("user1", {"admin"})
        ex = SkillExecutor(registry=reg, permission_checker=checker)
        result = await ex.execute("perm_skill", {}, user_id="user1")
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_result_is_cached_on_second_call(self) -> None:
        reg = SkillRegistry()
        call_count = 0

        class _CountSkill(BaseSkill):
            @property
            def definition(self) -> SkillDefinition:
                return SkillDefinition(
                    name="counter",
                    description="Counts calls.",
                    parameters_schema={"type": "object", "properties": {}, "required": []},
                    category="test",
                    cacheable=True,
                )

            async def execute(self, **kwargs):
                nonlocal call_count
                call_count += 1
                return Ok(SkillResult(skill_name="counter", success=True, output={}))

        reg.register(_CountSkill())
        cache = SkillResultCache()
        ex = SkillExecutor(registry=reg, cache=cache)

        await ex.execute("counter", {})
        await ex.execute("counter", {})

        assert call_count == 1  # second call served from cache

    @pytest.mark.asyncio
    async def test_execute_without_user_id_skips_permission_check(self) -> None:
        reg = SkillRegistry()
        reg.register(_PermSkill())
        checker = PermissionChecker()  # no grants
        ex = SkillExecutor(registry=reg, permission_checker=checker)
        # No user_id means no permission check
        result = await ex.execute("perm_skill", {})
        assert result.is_ok()
