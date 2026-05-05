"""Tests for the query_stats admin widget handler."""

from __future__ import annotations

from unittest.mock import MagicMock

from lexigram.contracts.admin import StatContent, Tone, WidgetParams
from lexigram.sql.admin.handlers.query_stats import QueryStatsWidgetHandler


def _fake_db() -> MagicMock:
    return MagicMock()


async def test_query_stats_handler_returns_single_stat_content() -> None:
    result = await QueryStatsWidgetHandler(db=_fake_db()).get_data(WidgetParams())
    content = result.unwrap()
    assert isinstance(content, StatContent)
    assert len(content.stats) == 4


async def test_query_stats_copies_template_values_exactly() -> None:
    result = await QueryStatsWidgetHandler(db=_fake_db()).get_data(WidgetParams())
    content = result.unwrap()
    total, avg, slow, errors = content.stats
    assert total.label == "Total Queries"
    assert total.value == "1250"
    assert avg.label == "Avg Duration"
    assert avg.value == "12.5ms"
    assert slow.label == "Slow Queries"
    assert slow.value == "3"
    assert errors.label == "Errors"
    assert errors.value == "0"


async def test_query_stats_mirrors_per_line_tone_classes() -> None:
    result = await QueryStatsWidgetHandler(db=_fake_db()).get_data(WidgetParams())
    content = result.unwrap()
    total, avg, slow, errors = content.stats
    assert total.tone is Tone.DEFAULT
    assert avg.tone is Tone.DEFAULT
    assert slow.tone is Tone.WARNING
    assert errors.tone is Tone.DANGER


__all__ = [
    "test_query_stats_handler_returns_single_stat_content",
    "test_query_stats_copies_template_values_exactly",
    "test_query_stats_mirrors_per_line_tone_classes",
]