"""Tests for composition utilities: SkillChain, SkillRouter, SkillPipeline, ParallelSkills."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.ai.skills import SkillResult
from lexigram.result import Err, Ok

from lexigram.ai.skills.composition.chain import SkillChain
from lexigram.ai.skills.composition.parallel import ParallelSkills
from lexigram.ai.skills.composition.pipeline import SkillPipeline
from lexigram.ai.skills.composition.router import SkillRouter
from lexigram.ai.skills.exceptions import SkillExecutionError, SkillRoutingError


def _ok_executor(*outputs: dict) -> MagicMock:
    """Build a mock executor that returns successive Ok results."""
    executor = MagicMock()
    executor.execute = AsyncMock(
        side_effect=[
            Ok(SkillResult(skill_name=f"skill_{i}", success=True, output=out))
            for i, out in enumerate(outputs)
        ]
    )
    return executor


def _err_executor(msg: str = "boom") -> MagicMock:
    executor = MagicMock()
    executor.execute = AsyncMock(
        return_value=Err(SkillExecutionError(msg))
    )
    return executor


class TestSkillChain:
    """Tests for SkillChain sequential execution."""

    @pytest.mark.asyncio
    async def test_single_step_passes_params(self) -> None:
        ex = _ok_executor({"greeting": "hi"})
        chain = SkillChain([("echo", {})])
        result = await chain.execute(ex, {"msg": "hi"})
        assert result.is_ok()
        assert result.unwrap().output == {"greeting": "hi"}

    @pytest.mark.asyncio
    async def test_output_piped_to_next_step(self) -> None:
        ex = _ok_executor({"answer": 42}, {"doubled": 84})
        chain = SkillChain([
            ("first", {"answer": "value"}),
            ("second", {}),
        ])
        result = await chain.execute(ex, {"n": 1})
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_error_in_step_aborts_chain(self) -> None:
        ex = _err_executor("step_failed")
        chain = SkillChain([("fail_skill", {}), ("echo", {})])
        result = await chain.execute(ex, {})
        assert result.is_err()
        # second skill must not be called
        assert ex.execute.call_count == 1


class TestSkillRouter:
    """Tests for SkillRouter conditional dispatch."""

    @pytest.mark.asyncio
    async def test_first_matching_route_is_used(self) -> None:
        ex = _ok_executor({"routed": True})
        router = SkillRouter()
        router.add_route("premium", condition=lambda p: p.get("tier") == "premium")
        router.add_route("basic", condition=lambda p: True)
        result = await router.execute(ex, {"tier": "premium"})
        assert result.is_ok()
        ex.execute.assert_called_once_with("premium", {"tier": "premium"})

    @pytest.mark.asyncio
    async def test_fallback_used_when_no_route_matches(self) -> None:
        ex = _ok_executor({"fallback": True})
        router = SkillRouter(fallback="default")
        router.add_route("never", condition=lambda p: False)
        result = await router.execute(ex, {})
        assert result.is_ok()
        ex.execute.assert_called_once_with("default", {})

    @pytest.mark.asyncio
    async def test_error_when_no_route_and_no_fallback(self) -> None:
        ex = _ok_executor({})
        router = SkillRouter()
        router.add_route("never", condition=lambda p: False)
        result = await router.execute(ex, {})
        assert result.is_err()
        assert isinstance(result.unwrap_err(), SkillRoutingError)


class TestSkillPipeline:
    """Tests for SkillPipeline enrichment."""

    @pytest.mark.asyncio
    async def test_output_key_stored_in_context(self) -> None:
        ex = _ok_executor({"clean": "hello"})
        pipeline = SkillPipeline()
        pipeline.add_stage("normalise", output_key="normalized")
        result = await pipeline.execute(ex, {"raw": "  hello  "})
        assert result.is_ok()
        assert "normalized" in result.unwrap().output

    @pytest.mark.asyncio
    async def test_no_output_key_merges_into_context(self) -> None:
        ex = _ok_executor({"extra_field": "value"})
        pipeline = SkillPipeline()
        pipeline.add_stage("enrich")
        result = await pipeline.execute(ex, {"base": 1})
        assert result.is_ok()
        assert "extra_field" in result.unwrap().output

    @pytest.mark.asyncio
    async def test_error_aborts_pipeline(self) -> None:
        ex = _err_executor("stage_error")
        pipeline = SkillPipeline()
        pipeline.add_stage("fail_stage")
        result = await pipeline.execute(ex, {})
        assert result.is_err()


class TestParallelSkills:
    """Tests for ParallelSkills concurrent fan-out."""

    @pytest.mark.asyncio
    async def test_outputs_aggregated_by_skill_name(self) -> None:
        output_a = {"value": 1}
        output_b = {"value": 2}

        executor = MagicMock()
        executor.execute = AsyncMock(
            side_effect=[
                Ok(SkillResult(skill_name="skill_a", success=True, output=output_a)),
                Ok(SkillResult(skill_name="skill_b", success=True, output=output_b)),
            ]
        )

        parallel = ParallelSkills(["skill_a", "skill_b"])
        result = await parallel.execute(executor, {"x": 0})

        assert result.is_ok()
        combined = result.unwrap().output
        assert combined["skill_a"] == output_a
        assert combined["skill_b"] == output_b

    @pytest.mark.asyncio
    async def test_skill_error_recorded_in_errors_key(self) -> None:
        executor = MagicMock()
        executor.execute = AsyncMock(
            side_effect=[
                Ok(SkillResult(skill_name="ok_skill", success=True, output={"ok": True})),
                Err(SkillExecutionError("bad")),
            ]
        )

        parallel = ParallelSkills(["ok_skill", "bad_skill"])
        result = await parallel.execute(executor, {})

        assert result.is_ok()
        output = result.unwrap().output
        assert "ok_skill" in output
        assert "_errors" in output
        assert "bad_skill" in output["_errors"]
