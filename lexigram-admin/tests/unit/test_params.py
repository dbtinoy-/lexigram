"""Tests for parse_widget_params HTTP boundary helper."""

from __future__ import annotations

import pytest

from lexigram.admin.params import parse_widget_params
from lexigram.contracts.admin.types import WidgetParams


class TestParseWidgetParams:
    def test_defaults(self) -> None:
        result = parse_widget_params({})
        assert result.page == 1
        assert result.page_size == 20
        assert result.time_window_minutes == 60

    def test_parses_valid_values(self) -> None:
        result = parse_widget_params(
            {"page": "3", "page_size": "50", "time_window_minutes": "15"}
        )
        assert result.page == 3
        assert result.page_size == 50
        assert result.time_window_minutes == 15

    def test_clamps_page_size_max(self) -> None:
        result = parse_widget_params({"page_size": "999"})
        assert result.page_size == 100

    def test_clamps_page_min(self) -> None:
        result = parse_widget_params({"page": "0"})
        assert result.page == 1

    def test_invalid_int_falls_back_to_default(self) -> None:
        result = parse_widget_params({"page": "abc"})
        assert result.page == 1

    def test_preserves_raw_params(self) -> None:
        result = parse_widget_params({"page": "2", "custom": "val"})
        assert ("page", "2") in result.raw
        assert ("custom", "val") in result.raw

    def test_returns_widget_params(self) -> None:
        result = parse_widget_params({})
        assert isinstance(result, WidgetParams)
