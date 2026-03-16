from __future__ import annotations

from typing import Any, Literal

from lexigram.ui.core.base import Component, el


class Skeleton(Component):
    """Skeleton loader placeholder for content.

    Args:
        variant: Shape variant (text, circular, rectangular)
        width: CSS width value
        height: CSS height value
        count: Number of skeleton lines (for text variant)
    """

    def __init__(
        self,
        variant: Literal["text", "circular", "rectangular", "table"] = "text",
        width: str = "100%",
        height: str | None = None,
        count: int = 1,
        **props,
    ) -> None:
        super().__init__(
            variant=variant,
            width=width,
            height=height,
            count=count,
            **props,
        )
        self.variant = variant
        self.width = width
        self.height = height
        self.count = count

    def render(self) -> Any:
        if self.variant == "text":
            items = []
            for i in range(self.count):
                # Last item is shorter
                item_width = "80%" if i == self.count - 1 else self.width
                items.append(
                    el(
                        "div",
                        class_="h-4 bg-muted rounded-md animate-pulse mb-2",
                        style=f"width: {item_width}",
                    ),
                )
            return el("div", *items, class_="space-y-2", aria_hidden="true")

        if self.variant == "circular":
            size = self.height or "3rem"
            return el(
                "div",
                class_="bg-muted rounded-full animate-pulse",
                style=f"width: {size}; height: {size}",
                aria_hidden="true",
            )

        if self.variant == "table":
            items = []
            for _ in range(self.count):
                items.append(
                    el(
                        "div",
                        class_="h-8 bg-muted rounded-md animate-pulse mb-2",
                        style=f"width: {self.width}",
                    ),
                )
            return el("div", *items, class_="space-y-1", aria_hidden="true")

        # rectangular
        h = self.height or "8rem"
        return el(
            "div",
            class_="bg-muted rounded-md animate-pulse",
            style=f"width: {self.width}; height: {h}",
            aria_hidden="true",
        )
