"""Tests for the failed_messages admin widget handler."""

from __future__ import annotations

from lexigram.contracts.admin import StatContent, Tone, WidgetParams
from lexigram.queue.admin.handlers.failed_messages import FailedMessagesWidgetHandler


class _FakeDlq:
    def __init__(self, dead_letter_count: int = 0) -> None:
        self._count = dead_letter_count

    def get_stats(self) -> dict[str, int | float | str] | None:
        return {"dead_letter_count": self._count}


async def test_failed_messages_reads_capability_stats() -> None:
    handler = FailedMessagesWidgetHandler(_FakeDlq(dead_letter_count=3))
    result = await handler.get_data(WidgetParams())
    content = result.unwrap()
    assert isinstance(content, StatContent)
    assert content.stats[0].label == "Failed messages"
    assert content.stats[0].value == "3"
    assert content.stats[0].tone is Tone.DANGER


async def test_failed_messages_success_when_clear() -> None:
    handler = FailedMessagesWidgetHandler(_FakeDlq())
    result = await handler.get_data(WidgetParams())
    content = result.unwrap()
    assert isinstance(content, StatContent)
    assert content.stats[0].value == "✓ No failures"
    assert content.stats[0].tone is Tone.SUCCESS


async def test_failed_messages_degrades_without_capability() -> None:
    handler = FailedMessagesWidgetHandler(object())
    result = await handler.get_data(WidgetParams())
    content = result.unwrap()
    assert isinstance(content, StatContent)
    assert content.stats[0].value == "Unavailable"
    assert content.stats[0].tone is Tone.WARNING


__all__ = [
    "test_failed_messages_degrades_without_capability",
    "test_failed_messages_reads_capability_stats",
    "test_failed_messages_success_when_clear",
]