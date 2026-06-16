"""Tests for the failed_logins admin widget handler."""

from __future__ import annotations

from unittest.mock import MagicMock

from lexigram.auth.admin.handlers.failed_logins import FailedLoginsWidgetHandler
from lexigram.contracts.admin import StatContent, Tone, WidgetParams


async def test_failed_logins_handler_returns_stat_content() -> None:
    result = await FailedLoginsWidgetHandler(session_manager=MagicMock()).get_data(
        WidgetParams()
    )
    content = result.unwrap()
    assert isinstance(content, StatContent)


async def test_failed_logins_stats_mirror_template() -> None:
    result = await FailedLoginsWidgetHandler(session_manager=MagicMock()).get_data(
        WidgetParams()
    )
    content = result.unwrap()
    count = content.stats[0]
    assert count.label == "Failed Logins (1 hour)"
    assert count.value == "0"


async def test_failed_logins_no_unique_ips_stat_when_zero() -> None:
    result = await FailedLoginsWidgetHandler(session_manager=MagicMock()).get_data(
        WidgetParams()
    )
    content = result.unwrap()
    assert len(content.stats) == 1


def test_failed_logins_tone_is_danger_when_elevated() -> None:
    handler = FailedLoginsWidgetHandler(session_manager=MagicMock())
    content = handler._build_content(3, 2, is_elevated=True)
    stat = content.stats[0]
    assert stat.tone is Tone.DANGER
    assert stat.value == "3"


def test_failed_logins_tone_is_static_when_not_elevated() -> None:
    handler = FailedLoginsWidgetHandler(session_manager=MagicMock())
    content = handler._build_content(3, 2, is_elevated=False)
    stat = content.stats[0]
    assert stat.tone is Tone.DEFAULT


__all__ = [
    "test_failed_logins_handler_returns_stat_content",
    "test_failed_logins_no_unique_ips_stat_when_zero",
    "test_failed_logins_stats_mirror_template",
    "test_failed_logins_tone_is_danger_when_elevated",
    "test_failed_logins_tone_is_static_when_not_elevated",
]