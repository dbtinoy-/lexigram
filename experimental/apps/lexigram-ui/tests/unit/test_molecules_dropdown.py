"""Tests for Dropdown molecule."""
from __future__ import annotations

from lexigram.ui.core.base import el
from lexigram.ui.molecules.dropdown import Dropdown


class TestDropdown:
    def test_dropdown_renders_trigger(self) -> None:
        d = Dropdown(trigger="Menu", items=[el("a", "Item 1")])
        result = str(d)
        assert "Menu" in result

    def test_dropdown_renders_items(self) -> None:
        d = Dropdown(
            trigger="Menu",
            items=[el("a", "Item 1"), el("a", "Item 2")],
        )
        result = str(d)
        assert "Item 1" in result
        assert "Item 2" in result

    def test_dropdown_position_right_default(self) -> None:
        d = Dropdown(trigger="M", items=[el("a", "i")])
        result = str(d)
        assert "right-0" in result

    def test_dropdown_position_left(self) -> None:
        d = Dropdown(trigger="M", items=[el("a", "i")], position="left")
        result = str(d)
        assert "left-0" in result

    def test_dropdown_direction_up(self) -> None:
        d = Dropdown(trigger="M", items=[el("a", "i")], direction="up")
        result = str(d)
        assert "bottom-full" in result

    def test_dropdown_has_alpine_data(self) -> None:
        d = Dropdown(trigger="M", items=[el("a", "i")])
        result = str(d)
        assert "x-data" in result
        assert "open" in result

    def test_dropdown_up_with_right(self) -> None:
        d = Dropdown(
            trigger="M", items=[el("a", "i")], direction="up", position="right"
        )
        result = str(d)
        assert "origin-bottom-right" in result

    def test_dropdown_up_with_left(self) -> None:
        d = Dropdown(
            trigger="M", items=[el("a", "i")], direction="up", position="left"
        )
        result = str(d)
        assert "origin-bottom-left" in result
