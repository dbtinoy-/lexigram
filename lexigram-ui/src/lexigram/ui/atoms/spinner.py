from __future__ import annotations

from typing import Any, Literal

from lexigram.ui.core.base import Component, el


class Spinner(Component):
    """Circular loading spinner with size variants.

    Args:
        size: Size variant (sm=16px, md=24px, lg=32px, xl=48px)
        aria_label: Accessible label announced to screen readers (default: "Loading...")
    """

    def __init__(
        self,
        size: Literal["sm", "md", "lg", "xl"] = "md",
        aria_label: str = "Loading...",
        **props,
    ) -> None:
        super().__init__(size=size, **props)
        self.size = size
        self.aria_label = aria_label

    def render(self) -> Any:
        size_map = {
            "sm": "w-4 h-4",
            "md": "w-6 h-6",
            "lg": "w-8 h-8",
            "xl": "w-12 h-12",
        }

        return el(
            "svg",
            el(
                "circle",
                cx="12",
                cy="12",
                r="10",
                stroke="currentColor",
                stroke_width="4",
                fill="none",
                class_="opacity-25",
            ),
            el(
                "path",
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z",
                fill="currentColor",
                class_="opacity-75",
            ),
            role="status",
            aria_live="polite",
            aria_label=self.aria_label,
            class_=f"{size_map[self.size]} text-primary animate-spin opacity-70",
            xmlns="http://www.w3.org/2000/svg",
            viewBox="0 0 24 24",
        )
