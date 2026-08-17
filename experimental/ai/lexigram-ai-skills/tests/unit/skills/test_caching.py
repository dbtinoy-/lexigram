"""Tests for SkillResultCache."""

from __future__ import annotations

import pytest

from lexigram.contracts.ai.skills import SkillResult

from lexigram.ai.skills.caching.skill_cache import SkillResultCache


class TestSkillResultCache:
    """Tests for SkillResultCache two-tier caching."""

    @pytest.fixture
    def cache(self) -> SkillResultCache:
        return SkillResultCache()

    @pytest.fixture
    def sample_result(self) -> SkillResult:
        return SkillResult(skill_name="echo", success=True, output={"msg": "hi"})

    @pytest.mark.asyncio
    async def test_get_returns_none_on_cache_miss(self, cache) -> None:
        result = await cache.get("echo", {"x": 1})
        assert result is None

    @pytest.mark.asyncio
    async def test_set_then_get_returns_result(self, cache, sample_result) -> None:
        await cache.set("echo", {"x": 1}, sample_result)
        cached = await cache.get("echo", {"x": 1})
        assert cached is not None
        assert cached.skill_name == "echo"
        assert cached.output == {"msg": "hi"}

    @pytest.mark.asyncio
    async def test_different_params_are_separate_entries(
        self, cache, sample_result
    ) -> None:
        await cache.set("echo", {"x": 1}, sample_result)
        miss = await cache.get("echo", {"x": 2})
        assert miss is None

    @pytest.mark.asyncio
    async def test_clear_removes_all_entries(self, cache, sample_result) -> None:
        await cache.set("echo", {"x": 1}, sample_result)
        cache.clear()
        assert await cache.get("echo", {"x": 1}) is None

    @pytest.mark.asyncio
    async def test_invalidate_removes_specific_entry(
        self, cache, sample_result
    ) -> None:
        r2 = SkillResult(skill_name="echo", success=True, output={"msg": "bye"})
        await cache.set("echo", {"x": 1}, sample_result)
        await cache.set("echo", {"x": 2}, r2)

        cache.invalidate("echo", {"x": 1})

        assert await cache.get("echo", {"x": 1}) is None
        assert await cache.get("echo", {"x": 2}) is not None

    @pytest.mark.asyncio
    async def test_different_skill_names_are_separate(
        self, cache, sample_result
    ) -> None:
        other = SkillResult(skill_name="math", success=True, output={"result": 4})
        await cache.set("echo", {"x": 1}, sample_result)
        await cache.set("math", {"x": 1}, other)

        assert (await cache.get("echo", {"x": 1})).skill_name == "echo"
        assert (await cache.get("math", {"x": 1})).skill_name == "math"
