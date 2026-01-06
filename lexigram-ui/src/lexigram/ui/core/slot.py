"""Slot/Outlet component for polymorphic asChild rendering."""

from __future__ import annotations

from typing import Any

from lexigram.ui.core.base import Component


class Slot(Component):
    """Renders its children directly without wrapping in a DOM node.

    Used internally by the ``asChild`` pattern to forward children
    through a parent component that delegates rendering.
    """

    def __init__(self, children: Any = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._slot_children = children

    def render(self) -> str:
        if self._slot_children is None:
            return ""
        if isinstance(self._slot_children, Component):
            return self._slot_children.render()
        return str(self._slot_children)
