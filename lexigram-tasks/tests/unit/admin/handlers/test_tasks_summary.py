"""Tests for the tasks_summary admin widget handler."""

from __future__ import annotations

import pytest

from lexigram.contracts.admin import StatContent, Tone, WidgetParams
from lexigram.tasks.admin.handlers.tasks_summary import TasksSummaryWidgetHandler


@pytest.mark.asyncio
async def test_tasks_summary_handler_returns_single_stat_content() -> None:
    result = await TasksSummaryWidgetHandler().get_data(WidgetParams())
    content = result.unwrap()
    assert isinstance(content, StatContent)
    assert len(content.stats) == 4


@pytest.mark.asyncio
async def test_tasks_summary_copies_template_cells_exactly() -> None:
    result = await TasksSummaryWidgetHandler().get_data(WidgetParams())
    content = result.unwrap()
    pending, running, completed, failed = content.stats
    assert pending.label == "Pending"
    assert pending.value == "0"
    assert running.label == "Running"
    assert running.value == "0"
    assert completed.label == "Completed"
    assert completed.value == "0"
    assert failed.label == "Failed"
    assert failed.value == "0"


@pytest.mark.asyncio
async def test_tasks_summary_mirrors_per_cell_tone_classes() -> None:
    result = await TasksSummaryWidgetHandler().get_data(WidgetParams())
    content = result.unwrap()
    pending, running, completed, failed = content.stats
    assert pending.tone is Tone.DEFAULT
    assert running.tone is Tone.INFO
    assert completed.tone is Tone.SUCCESS
    assert failed.tone is Tone.DANGER


__all__ = [
    "test_tasks_summary_handler_returns_single_stat_content",
    "test_tasks_summary_copies_template_cells_exactly",
    "test_tasks_summary_mirrors_per_cell_tone_classes",
]