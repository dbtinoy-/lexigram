from __future__ import annotations

from typing import Any

from lexigram.ui.atoms.spinner import Spinner
from lexigram.ui.core.base import Component, el


class LoadingOverlay(Component):
    """Full-screen or container loading overlay.

    Args:
        message: Optional loading message
        fullscreen: Whether to cover entire screen
    """

    def __init__(
        self,
        message: str = "Loading...",
        fullscreen: bool = True,
        **props,
    ) -> None:
        super().__init__(message=message, fullscreen=fullscreen, **props)
        self.message = message
        self.fullscreen = fullscreen

    def render(self) -> Any:
        position_class = "fixed inset-0" if self.fullscreen else "absolute inset-0"

        return el(
            "div",
            el(
                "div",
                Spinner(size="lg"),
                el(
                    "p",
                    self.message,
                    class_="mt-4 text-sm text-muted-foreground",
                )
                if self.message
                else "",
                class_="flex flex-col items-center justify-center",
            ),
            class_=f"{position_class} bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center",
            role="alert",
            aria_live="polite",
        )
