"""Tests for the dead_letter_count admin widget handler."""

from __future__ import annotations

from unittest.mock import MagicMock

from lexigram.contracts.admin import StatContent, Tone, WidgetParams
from lexigram.events.admin.handlers.dead_letter_count import (
    DeadLetterCountWidgetHandler,
)


async def test_dead_letter_count_handler_returns_stat_content() -> None:
    result = await DeadLetterCountWidgetHandler(event_bus=MagicMock()).get_data(
        WidgetParams()
    )
    content = result.unwrap()
    assert isinstance(content, StatContent)
    assert content.stats[0].value == "✓ Queue clear"
    assert content.stats[0].tone is Tone.SUCCESS


__all__ = ["test_dead_letter_count_handler_returns_stat_content"]