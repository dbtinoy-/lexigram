from __future__ import annotations

from typing import Any

from lexigram.ui.core.base import Component, el


class EmptyState(Component):
    """Empty state component for when no data is available.

    Args:
        title: Main heading
        message: Descriptive message
        icon: Optional emoji or icon
        action: Optional action button/link
    """

    def __init__(
        self,
        title: str = "No data available",
        message: str = "There's nothing to display yet.",
        icon: str = "📭",
        action: Any = None,
        **props,
    ) -> None:
        super().__init__(
            title=title,
            message=message,
            icon=icon,
            action=action,
            **props,
        )
        self.title = title
        self.message = message
        self.icon = icon
        self.action = action

    def render(self) -> Any:
        return el(
            "div",
            el(
                "div",
                el("div", self.icon, class_="text-6xl mb-4 opacity-50"),
                el(
                    "h3",
                    self.title,
                    class_="text-lg font-semibold text-foreground mb-2",
                ),
                el(
                    "p",
                    self.message,
                    class_="text-sm text-muted-foreground mb-4",
                ),
                self.action if self.action else "",
                class_="flex flex-col items-center justify-center text-center",
            ),
            class_="py-16 px-4",
        )
