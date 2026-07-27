"""Tests for the queue_depth admin widget handler."""

from __future__ import annotations

from lexigram.contracts.admin import StatContent, Tone, WidgetParams
from lexigram.queue.admin.handlers.queue_depth import QueueDepthWidgetHandler


class _FakeQueue:
    def __init__(self, pending: int = 0) -> None:
        self._pending = pending

    def get_stats(self) -> dict[str, int | float | str] | None:
        return {"pending": self._pending, "processing": 0}


async def test_queue_depth_reads_capability_stats() -> None:
    handler = QueueDepthWidgetHandler(_FakeQueue(pending=8))
    result = await handler.get_data(WidgetParams())
    content = result.unwrap()
    assert isinstance(content, StatContent)
    assert [s.label for s in content.stats] == ["Queue Depth"]
    assert content.stats[0].value == "8"
    assert content.stats[0].tone is Tone.SUCCESS


async def test_queue_depth_warns_at_high_depth() -> None:
    handler = QueueDepthWidgetHandler(_FakeQueue(pending=120))
    result = await handler.get_data(WidgetParams())
    content = result.unwrap()
    assert isinstance(content, StatContent)
    assert content.stats[0].value == "120"
    assert content.stats[0].tone is Tone.WARNING


async def test_queue_depth_degrades_without_capability() -> None:
    handler = QueueDepthWidgetHandler(object())
    result = await handler.get_data(WidgetParams())
    content = result.unwrap()
    assert isinstance(content, StatContent)
    assert content.stats[0].value == "Unavailable"
    assert content.stats[0].tone is Tone.WARNING


__all__ = [
    "test_queue_depth_degrades_without_capability",
    "test_queue_depth_reads_capability_stats",
    "test_queue_depth_warns_at_high_depth",
]