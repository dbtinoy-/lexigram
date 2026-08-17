"""Tests for Card molecule."""
from __future__ import annotations

from lexigram.ui.core.base import el
from lexigram.ui.molecules.card import Card


class TestCard:
    def test_card_renders(self) -> None:
        c = Card(title="My Card", content="Body content")
        result = str(c)
        assert "My Card" in result
        assert "Body content" in result

    def test_card_no_title(self) -> None:
        c = Card(content="Only body")
        result = str(c)
        assert "card-header" not in result
        assert "Only body" in result

    def test_card_no_content(self) -> None:
        c = Card(title="Title Only")
        result = str(c)
        assert "Title Only" in result

    def test_card_with_footer(self) -> None:
        c = Card(title="T", content="B", footer="Footer text")
        result = str(c)
        assert "card-footer" in result
        assert "Footer text" in result

    def test_card_with_actions(self) -> None:
        c = Card(title="T", content="B")
        c.props["actions"] = ["Save", "Cancel"]
        result = str(c)
        assert "Save" in result
        assert "Cancel" in result

    def test_card_with_custom_class(self) -> None:
        c = Card(title="T", class_="custom-card")
        result = str(c)
        assert "custom-card" in result

    def test_card_with_children(self) -> None:
        c = Card(title="T", content="B")
        c.children = [el("p", "extra child")]
        result = str(c)
        assert "extra child" in result

    def test_card_footer_with_element(self) -> None:
        c = Card(title="T", content="B")
        c.props["actions"] = [el("button", "Click")]
        result = str(c)
        assert "Click" in result
