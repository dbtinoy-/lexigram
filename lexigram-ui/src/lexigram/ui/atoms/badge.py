from __future__ import annotations

from typing import Any, Literal

from lexigram.ui.core.base import Component, el
from lexigram.ui.styles import get_semantic_classes

BadgeVariant = Literal[
    "default",
    "gray",
    "primary",
    "success",
    "warning",
    "danger",
    "info",
    "red",
    "yellow",
    "green",
    "blue",
    "indigo",
    "purple",
    "pink",
    "orange",
]


class Badge(Component):
    """Badge component for status indicators."""

    def __init__(self, text: str, variant: BadgeVariant = "default", **props) -> None:
        super().__init__(text=text, variant=variant, **props)
        self.text = text
        self.variant = variant

    def render(self) -> Any:
        variant_cls = get_semantic_classes(self.variant)

        return el(
            "span",
            self.text,
            role="status",
            class_=(
                "inline-flex items-center rounded-full border px-2.5 py-0.5 "
                "text-xs font-semibold transition-colors focus:outline-none "
                "focus:ring-2 focus:ring-ring focus:ring-offset-2 "
                f"border-transparent {variant_cls}"
            ),
        )
