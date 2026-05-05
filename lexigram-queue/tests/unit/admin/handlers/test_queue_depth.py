"""Tests for the queue_depth admin widget handler."""

from __future__ import annotations

from unittest.mock import MagicMock

from lexigram.contracts.admin import StatContent, Tone, WidgetParams
from lexigram.queue.admin.handlers.queue_depth import QueueDepthWidgetHandler


async def test_queue_depth_handler_returns_stat_content() -> None:
    result = await QueueDepthWidgetHandler(queue=MagicMock()).get_data(WidgetParams())
    content = result.unwrap()
    assert isinstance(content, StatContent)
    assert content.stats[0].label == "Queue"
    assert content.stats[0].value == "default"
    assert content.stats[1].value == "0"
    assert content.stats[1].tone is Tone.PRIMARY


async def test_queue_depth_stub_omits_max_stat_when_max_depth_unset() -> None:
    result = await QueueDepthWidgetHandler(queue=MagicMock()).get_data(WidgetParams())
    content = result.unwrap()
    assert isinstance(content, StatContent)
    assert [s.label for s in content.stats] == ["Queue", "Depth"]


__all__ = [
    "test_queue_depth_handler_returns_stat_content",
    "test_queue_depth_stub_omits_max_stat_when_max_depth_unset",
]