from __future__ import annotations

from typing import Any

from lexigram.ui.core.base import Component, el


class ErrorState(Component):
    """Error state component for when something goes wrong.

    Args:
        title: Error heading
        message: Error description
        action: Optional retry button/link
    """

    def __init__(
        self,
        title: str = "Something went wrong",
        message: str = "We encountered an error loading this data.",
        action: Any = None,
        **props: Any,
    ) -> None:
        super().__init__(title=title, message=message, action=action, **props)
        self.title = title
        self.message = message
        self.action = action

    def render(self) -> Any:
        from lexigram.ui.atoms.icons import get_icon

        return el(
            "div",
            el(
                "div",
                el(
                    "div",
                    get_icon("alert-circle", class_name="w-16 h-16 text-destructive"),
                    class_="mb-4",
                    aria_hidden="true",
                ),
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
            class_="py-16 px-4 bg-destructive/10 border border-destructive/30 rounded-lg",
            role="alert",
        )
