"""Tests for the avg_duration admin widget handler."""

from __future__ import annotations

import pytest

from lexigram.contracts.admin import StatContent, Tone, WidgetParams
from lexigram.tasks.admin.handlers.avg_duration import AvgDurationWidgetHandler


@pytest.mark.asyncio
async def test_avg_duration_handler_returns_single_stat_content() -> None:
    result = await AvgDurationWidgetHandler().get_data(WidgetParams())
    content = result.unwrap()
    assert isinstance(content, StatContent)
    assert len(content.stats) == 2


@pytest.mark.asyncio
async def test_avg_duration_copies_template_rows_exactly() -> None:
    result = await AvgDurationWidgetHandler().get_data(WidgetParams())
    content = result.unwrap()
    avg, p95 = content.stats
    assert avg.label == "Avg"
    assert avg.value == "0.0ms"
    assert p95.label == "P95"
    assert p95.value == "0.0ms"


@pytest.mark.asyncio
async def test_avg_duration_mirrors_per_row_tone_classes() -> None:
    result = await AvgDurationWidgetHandler().get_data(WidgetParams())
    content = result.unwrap()
    avg, p95 = content.stats
    assert avg.tone is Tone.DEFAULT
    assert p95.tone is Tone.WARNING


__all__ = [
    "test_avg_duration_handler_returns_single_stat_content",
    "test_avg_duration_copies_template_rows_exactly",
    "test_avg_duration_mirrors_per_row_tone_classes",
]