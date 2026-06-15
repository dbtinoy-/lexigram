"""Tests for the eviction_rate admin widget handler."""

from __future__ import annotations

from unittest.mock import MagicMock

from lexigram.cache.admin.handlers.eviction_rate import EvictionRateWidgetHandler
from lexigram.contracts.admin import StatContent, Tone, WidgetParams


def _fake_cache(total_evictions: int) -> MagicMock:
    cache = MagicMock()
    store = MagicMock()
    store.eviction_count = total_evictions
    cache._store = store
    return cache


async def test_eviction_rate_handler_returns_stat_content() -> None:
    result = await EvictionRateWidgetHandler(cache=_fake_cache(30)).get_data(
        WidgetParams()
    )
    content = result.unwrap()
    assert isinstance(content, StatContent)
    assert len(content.stats) == 2


async def test_eviction_rate_stats_use_static_neutral_tone() -> None:
    result = await EvictionRateWidgetHandler(cache=_fake_cache(1800)).get_data(
        WidgetParams(time_window_minutes=60)
    )
    content = result.unwrap()
    rate, total = content.stats
    assert rate.value == "0.5/s"
    assert rate.tone is Tone.DEFAULT
    assert total.value == "1800"
    assert total.tone is Tone.DEFAULT


__all__ = [
    "test_eviction_rate_handler_returns_stat_content",
    "test_eviction_rate_stats_use_static_neutral_tone",
]