"""Tests for Slot component."""

from __future__ import annotations

from lexigram.ui.core.base import Component, el
from lexigram.ui.core.slot import Slot


class Dummy(Component):
    tag = "div"

    def render(self) -> str:
        return str(el(self.tag, self.props, *self.children))


def test_slot_renders_text():
    slot = Slot("hello")
    assert slot.render() == "hello"


def test_slot_renders_component():
    inner = Dummy(children=["world"])
    slot = Slot(inner)
    assert slot.render() == "<div>world</div>"


def test_slot_empty():
    slot = Slot()
    assert slot.render() == ""
