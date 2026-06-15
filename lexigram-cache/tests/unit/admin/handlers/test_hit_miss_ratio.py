"""Tests for the hit_miss_ratio admin widget handler."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from lexigram.cache.admin.handlers.hit_miss_ratio import HitMissRatioWidgetHandler
from lexigram.contracts.admin import StatContent, Tone, WidgetParams


def _fake_cache(hits: int, misses: int) -> MagicMock:
    cache = MagicMock()
    stats = MagicMock()
    stats.hits = hits
    stats.misses = misses
    cache.get_stats = AsyncMock(return_value=stats)
    return cache


async def test_hit_miss_ratio_handler_returns_stat_content() -> None:
    result = await HitMissRatioWidgetHandler(cache=_fake_cache(100, 20)).get_data(
        WidgetParams(time_window_minutes=60)
    )
    content = result.unwrap()
    assert isinstance(content, StatContent)
    assert len(content.stats) == 3


async def test_hit_miss_ratio_rate_stat_mirrors_static_success_tone() -> None:
    result = await HitMissRatioWidgetHandler(cache=_fake_cache(100, 20)).get_data(
        WidgetParams(time_window_minutes=60)
    )
    content = result.unwrap()
    rate = content.stats[0]
    assert rate.value == "83.3%"
    assert rate.tone is Tone.SUCCESS
    assert "60m" in rate.label


async def test_hit_miss_ratio_counts_are_carried() -> None:
    result = await HitMissRatioWidgetHandler(cache=_fake_cache(100, 20)).get_data(
        WidgetParams(time_window_minutes=60)
    )
    content = result.unwrap()
    hits, misses = content.stats[1], content.stats[2]
    assert hits.value == "100"
    assert misses.value == "20"
    assert hits.tone is Tone.DEFAULT
    assert misses.tone is Tone.DEFAULT


__all__ = [
    "test_hit_miss_ratio_handler_returns_stat_content",
    "test_hit_miss_ratio_rate_stat_mirrors_static_success_tone",
    "test_hit_miss_ratio_counts_are_carried",
]