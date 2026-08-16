"""Tests for the consumer_lag admin widget handler."""

from __future__ import annotations

from lexigram.contracts.admin import StatContent, Tone, WidgetParams
from lexigram.queue.admin.handlers.consumer_lag import ConsumerLagWidgetHandler


class _FakeQueue:
    def __init__(self, processing: int = 0) -> None:
        self._processing = processing

    def get_stats(self) -> dict[str, int | float | str] | None:
        return {"pending": 0, "processing": self._processing}


async def test_consumer_lag_reads_capability_stats() -> None:
    handler = ConsumerLagWidgetHandler(_FakeQueue(processing=5))
    result = await handler.get_data(WidgetParams())
    content = result.unwrap()
    assert isinstance(content, StatContent)
    assert [s.label for s in content.stats] == ["Consumer Lag"]
    assert content.stats[0].value == "5"
    assert content.stats[0].tone is Tone.SUCCESS


async def test_consumer_lag_warns_at_high_lag() -> None:
    handler = ConsumerLagWidgetHandler(_FakeQueue(processing=150))
    result = await handler.get_data(WidgetParams())
    content = result.unwrap()
    assert isinstance(content, StatContent)
    assert content.stats[0].value == "150"
    assert content.stats[0].tone is Tone.WARNING


async def test_consumer_lag_degrades_without_capability() -> None:
    handler = ConsumerLagWidgetHandler(object())
    result = await handler.get_data(WidgetParams())
    content = result.unwrap()
    assert isinstance(content, StatContent)
    assert content.stats[0].value == "Unavailable"
    assert content.stats[0].tone is Tone.WARNING


__all__ = [
    "test_consumer_lag_degrades_without_capability",
    "test_consumer_lag_reads_capability_stats",
    "test_consumer_lag_warns_at_high_lag",
]