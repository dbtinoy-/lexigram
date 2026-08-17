from __future__ import annotations

from typing import Any, Literal

from lexigram.ui.core.base import Component, el


class ProgressBar(Component):
    """Linear progress bar with percentage display.

    Args:
        value: Current progress value
        max: Maximum value (default 100)
        label: Optional label text
        show_percentage: Whether to show percentage text
        size: Height variant (sm, md, lg)
    """

    def __init__(
        self,
        value: int,
        max_value: int = 100,
        label: str | None = None,
        show_percentage: bool = True,
        size: Literal["sm", "md", "lg"] = "md",
        **props: Any,
    ) -> None:
        super().__init__(
            value=value,
            max=max_value,
            label=label,
            show_percentage=show_percentage,
            size=size,
            **props,
        )
        self.value = value
        self.max = max_value
        self.label = label
        self.show_percentage = show_percentage
        self.size = size

    def render(self) -> Any:
        percentage = int((self.value / self.max) * 100) if self.max > 0 else 0

        size_map = {"sm": "h-1", "md": "h-2", "lg": "h-3"}

        header = ""
        if self.label or self.show_percentage:
            header = el(
                "div",
                el(
                    "span",
                    self.label or "",
                    class_="text-sm font-medium text-foreground opacity-70",
                )
                if self.label
                else "",
                el(
                    "span",
                    f"{percentage}%",
                    class_="text-sm font-medium text-foreground opacity-70",
                )
                if self.show_percentage
                else "",
                class_="flex justify-between mb-1",
            )

        return el(
            "div",
            header,
            el(
                "div",
                el(
                    "div",
                    role="progressbar",
                    aria_valuenow=str(self.value),
                    aria_valuemin="0",
                    aria_valuemax=str(self.max),
                    aria_label=self.label or f"{percentage}%",
                    class_=f"bg-primary {size_map[self.size]} rounded-full transition-all duration-300",
                    style=f"width: {percentage}%",
                ),
                class_=f"w-full bg-secondary rounded-full {size_map[self.size]} overflow-hidden",
            ),
            class_="w-full",
        )
