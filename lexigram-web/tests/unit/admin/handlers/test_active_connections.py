"""Tests for the active_connections admin widget handler."""

from __future__ import annotations

from lexigram.contracts.admin import StatContent, Tone, WidgetParams
from lexigram.web.admin.handlers.active_connections import (
    ActiveConnectionsWidgetHandler,
)


async def test_active_connections_handler_returns_stat_content() -> None:
    result = await ActiveConnectionsWidgetHandler().get_data(WidgetParams())
    content = result.unwrap()
    assert isinstance(content, StatContent)
    assert content.stats[0].value == "42"
    assert content.stats[0].tone is Tone.PRIMARY


__all__ = ["test_active_connections_handler_returns_stat_content"]
