"""Tests for the pool_utilization admin widget handler."""

from __future__ import annotations

from unittest.mock import MagicMock

from lexigram.contracts.admin import StatContent, Tone, WidgetParams
from lexigram.sql.admin.handlers.pool_utilization import PoolUtilizationWidgetHandler


def _fake_db() -> MagicMock:
    return MagicMock()


async def test_pool_utilization_handler_returns_stat_content() -> None:
    result = await PoolUtilizationWidgetHandler(db=_fake_db()).get_data(WidgetParams())
    content = result.unwrap()
    assert isinstance(content, StatContent)
    assert len(content.stats) == 2


async def test_pool_utilization_stats_mirror_template_lines() -> None:
    result = await PoolUtilizationWidgetHandler(db=_fake_db()).get_data(WidgetParams())
    content = result.unwrap()
    active, utilization = content.stats
    assert active.label == "Active Connections"
    assert active.value == "8/20"
    assert utilization.label == "Utilization"
    assert utilization.value == "40.0%"


async def test_pool_utilization_uses_static_tone_no_thresholds() -> None:
    result = await PoolUtilizationWidgetHandler(db=_fake_db()).get_data(WidgetParams())
    content = result.unwrap()
    assert content.stats[0].tone is Tone.PRIMARY
    assert content.stats[1].tone is Tone.DEFAULT


__all__ = [
    "test_pool_utilization_handler_returns_stat_content",
    "test_pool_utilization_stats_mirror_template_lines",
    "test_pool_utilization_uses_static_tone_no_thresholds",
]