"""Tests for the events_throughput admin widget handler."""

from __future__ import annotations

from unittest.mock import MagicMock

from lexigram.contracts.admin import StatContent, Tone, WidgetParams
from lexigram.events.admin.handlers.events_throughput import (
    EventsThroughputWidgetHandler,
)


async def test_events_throughput_handler_returns_stat_content() -> None:
    result = await EventsThroughputWidgetHandler(event_bus=MagicMock()).get_data(
        WidgetParams()
    )
    content = result.unwrap()
    assert isinstance(content, StatContent)
    assert content.stats[0].value == "0.0/s"
    assert content.stats[0].tone is Tone.DEFAULT
    assert content.stats[1].value == "0"
    assert content.stats[1].label == "Total (60m)"


__all__ = ["test_events_throughput_handler_returns_stat_content"]