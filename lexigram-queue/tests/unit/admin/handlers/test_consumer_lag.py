"""Tests for the consumer_lag admin widget handler."""

from __future__ import annotations

from unittest.mock import MagicMock

from lexigram.contracts.admin import StatContent, Tone, WidgetParams
from lexigram.queue.admin.handlers.consumer_lag import ConsumerLagWidgetHandler


async def test_consumer_lag_handler_returns_stat_content() -> None:
    result = await ConsumerLagWidgetHandler(queue=MagicMock()).get_data(WidgetParams())
    content = result.unwrap()
    assert isinstance(content, StatContent)
    assert content.stats[0].label == "Lag (messages)"
    assert content.stats[0].value == "0"
    assert content.stats[0].tone is Tone.DEFAULT
    assert content.stats[1].label == "Lag (seconds)"
    assert content.stats[1].value == "~0.0s"


__all__ = ["test_consumer_lag_handler_returns_stat_content"]