"""Tests for the request_rate admin widget handler."""

from __future__ import annotations

from lexigram.contracts.admin import StatContent
from lexigram.contracts.admin import Tone
from lexigram.contracts.admin import WidgetParams
from lexigram.web.admin.handlers.request_rate import RequestRateWidgetHandler


async def test_request_rate_handler_returns_stat_content() -> None:
    result = await RequestRateWidgetHandler().get_data(WidgetParams())
    content = result.unwrap()
    assert isinstance(content, StatContent)
    assert content.stats[0].value == "12.5"
    assert content.stats[0].label == "Requests/sec"
    assert content.stats[2].label == "Error rate"
    assert content.stats[2].value == "0.5%"
    assert content.stats[2].tone is Tone.SUCCESS


__all__ = ["test_request_rate_handler_returns_stat_content"]