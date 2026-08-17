"""Tests for ConditionalSkill."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.ai.skills.composition.conditional import ConditionalSkill
from lexigram.ai.skills.exceptions import SkillRoutingError
from lexigram.contracts.ai.skills import SkillResult
from lexigram.result import Err, Ok


def _ok_executor(skill_name: str = "test") -> MagicMock:
    executor = MagicMock()
    executor.execute = AsyncMock(
        return_value=Ok(SkillResult(skill_name=skill_name, success=True, output={}))
    )
    return executor


def _err_executor(msg: str = "boom") -> MagicMock:
    executor = MagicMock()
    executor.execute = AsyncMock(
        return_value=Err(SkillRoutingError(msg))
    )
    return executor


class TestConditionalSkill:
    """Tests for ConditionalSkill conditional execution."""

    @pytest.mark.asyncio
    async def test_condition_true_executes_if_true(self) -> None:
        ex = _ok_executor("premium")
        cond = ConditionalSkill(
            condition=lambda p: p.get("premium", False),
            if_true="premium_skill",
            if_false="basic_skill",
        )
        result = await cond.execute(ex, {"query": "test", "premium": True})

        assert result.is_ok()
        ex.execute.assert_called_once_with("premium_skill", {"query": "test", "premium": True})

    @pytest.mark.asyncio
    async def test_condition_false_without_if_false_returns_err(self) -> None:
        ex = _ok_executor()
        cond = ConditionalSkill(
            condition=lambda p: p.get("premium", False),
            if_true="premium_skill",
            if_false=None,
        )
        result = await cond.execute(ex, {"query": "test", "premium": False})

        assert result.is_err()
        assert isinstance(result.unwrap_err(), SkillRoutingError)
        assert "no if_false skill is configured" in str(result.unwrap_err())

    @pytest.mark.asyncio
    async def test_condition_false_with_if_false_executes_fallback(self) -> None:
        ex = _ok_executor("basic")
        cond = ConditionalSkill(
            condition=lambda p: p.get("premium", False),
            if_true="premium_skill",
            if_false="basic_skill",
        )
        result = await cond.execute(ex, {"query": "test", "premium": False})

        assert result.is_ok()
        ex.execute.assert_called_once_with("basic_skill", {"query": "test", "premium": False})

    @pytest.mark.asyncio
    async def test_condition_raises_exception_returns_err(self) -> None:
        ex = _ok_executor()
        cond = ConditionalSkill(
            condition=lambda p: p["missing_key"],
            if_true="true_skill",
            if_false="false_skill",
        )
        result = await cond.execute(ex, {})

        assert result.is_err()
        assert isinstance(result.unwrap_err(), SkillRoutingError)
        assert "Condition evaluation failed" in str(result.unwrap_err())
