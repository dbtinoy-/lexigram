from __future__ import annotations

from typing import Any

from lexigram.ui.core.base import Component, el, raw, render_to_string


class Popover(Component):
    """
    Popover component for richer content than tooltips.
    """

    def __init__(
        self,
        trigger: str | Any,
        position: str = "bottom",
        width: str = "md",
        **props: Any,
    ) -> None:
        super().__init__(trigger=trigger, position=position, width=width, **props)
        self.trigger = trigger
        self.position = position
        self.width = width

    def render(self) -> Any:
        width_cls = {"sm": "w-48", "md": "w-72", "lg": "w-96", "xl": "w-[30rem]"}.get(
            self.width,
            "w-72",
        )

        children_html = [
            raw(render_to_string(c))
            if hasattr(c, "__html__") or hasattr(c, "render")
            else str(c)
            for c in self.children
        ]

        return el(
            "div",
            {"x-data": "{ open: false }", "class": "relative inline-block"},
            el(
                "div",
                {
                    "x-on:click": "open = !open",
                    "x-on:click.outside": "open = false",
                    "class": "cursor-pointer",
                    "tabindex": "0",
                    "role": "button",
                    ":aria-expanded": "open",
                },
                self.trigger,
            ),
            el(
                "div",
                {
                    "x-show": "open",
                    "x-transition": "",
                    "class": f"absolute z-10 mt-2 {width_cls} px-4 transform -translate-x-1/2 left-1/2 sm:px-0 lg:max-w-3xl",
                },
                el(
                    "div",
                    {
                        "class": "overflow-hidden rounded-lg shadow-lg ring-1 ring-border/10",
                    },
                    el(
                        "div",
                        {
                            "class": "relative grid bg-popover text-popover-foreground p-4 gap-4"
                        },
                        *children_html,
                    ),
                ),
            ),
        )
