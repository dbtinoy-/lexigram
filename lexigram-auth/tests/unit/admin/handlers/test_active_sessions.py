"""Tests for the active_sessions admin widget handler."""

from __future__ import annotations

from unittest.mock import MagicMock

from lexigram.auth.admin.handlers.active_sessions import ActiveSessionsWidgetHandler
from lexigram.contracts.admin import StatContent, Tone, WidgetParams


async def test_active_sessions_handler_returns_stat_content() -> None:
    result = await ActiveSessionsWidgetHandler(session_manager=MagicMock()).get_data(
        WidgetParams()
    )
    content = result.unwrap()
    assert isinstance(content, StatContent)


async def test_active_sessions_stats_mirror_template() -> None:
    result = await ActiveSessionsWidgetHandler(session_manager=MagicMock()).get_data(
        WidgetParams()
    )
    content = result.unwrap()
    active = content.stats[0]
    assert active.label == "Currently Active"
    assert active.value == "0"
    assert active.tone is Tone.PRIMARY


async def test_active_sessions_no_peak_stat_when_zero() -> None:
    result = await ActiveSessionsWidgetHandler(session_manager=MagicMock()).get_data(
        WidgetParams()
    )
    content = result.unwrap()
    assert len(content.stats) == 1


async def test_active_sessions_uses_static_tone_no_threshold_ladder() -> None:
    result = await ActiveSessionsWidgetHandler(session_manager=MagicMock()).get_data(
        WidgetParams()
    )
    content = result.unwrap()
    assert all(stat.tone is Tone.PRIMARY for stat in content.stats)


__all__ = [
    "test_active_sessions_handler_returns_stat_content",
    "test_active_sessions_no_peak_stat_when_zero",
    "test_active_sessions_stats_mirror_template",
    "test_active_sessions_uses_static_tone_no_threshold_ladder",
]