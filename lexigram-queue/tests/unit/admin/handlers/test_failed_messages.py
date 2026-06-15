"""Tests for the failed_messages admin widget handler."""

from __future__ import annotations

from unittest.mock import MagicMock

from lexigram.contracts.admin import StatContent, Tone, WidgetParams
from lexigram.queue.admin.handlers.failed_messages import FailedMessagesWidgetHandler


async def test_failed_messages_handler_returns_stat_content() -> None:
    result = await FailedMessagesWidgetHandler(queue=MagicMock()).get_data(
        WidgetParams()
    )
    content = result.unwrap()
    assert isinstance(content, StatContent)
    assert content.stats[0].value == "✓ No failures"
    assert content.stats[0].tone is Tone.SUCCESS


__all__ = ["test_failed_messages_handler_returns_stat_content"]