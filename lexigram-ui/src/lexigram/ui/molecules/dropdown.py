from __future__ import annotations

from typing import Any

from lexigram.ui.core.base import Component, el


class Dropdown(Component):
    """
    A refined dropdown menu component with positioning control.
    """

    def __init__(
        self,
        trigger: str | Any,
        items: list[Any],
        position: str = "right",
        direction: str = "down",
        **props,
    ) -> None:
        super().__init__(
            trigger=trigger,
            items=items,
            position=position,
            direction=direction,
            **props,
        )
        self.trigger = trigger
        self.items = items
        self.position = position
        self.direction = direction

    def render(self) -> Any:
        # Determine alignment classes
        origin_cls = "origin-top-right right-0"
        if self.position == "left":
            origin_cls = "origin-top-left left-0"

        # Determine direction classes
        mt_cls = "mt-2"
        origin_dir = "origin-top"
        if self.direction == "up":
            mt_cls = "mb-2 bottom-full"
            origin_dir = "origin-bottom"
            if self.position == "right":
                origin_cls = "origin-bottom-right right-0"
            else:
                origin_cls = "origin-bottom-left left-0"

        menu_items = [
            el(
                "div",
                item,
                role="menuitem",
                tabindex="-1",
                class_="cursor-pointer",
            )
            for item in self.items
        ]

        return el(
            "div",
            {
                "x-data": "{ open: false, focusedIndex: -1 }",
                "class": "relative inline-block text-left w-full",
                "x-on:keydown.escape.prevent": "open = false",
                "x-on:keydown.down.prevent": "focusedIndex = Math.min(focusedIndex + 1, "
                + str(len(self.items) - 1)
                + "); $nextTick(() => $el.querySelector('[role=menuitem]:nth-child(' + (focusedIndex + 1) + ')')?.focus())",
                "x-on:keydown.up.prevent": "focusedIndex = Math.max(focusedIndex - 1, 0); $nextTick(() => $el.querySelector('[role=menuitem]:nth-child(' + (focusedIndex + 1) + ')')?.focus())",
            },
            # Trigger
            el(
                "div",
                {
                    "x-ref": "trigger",
                    "x-on:click": "open = !open",
                    "x-on:click.outside": "open = false",
                    ":aria-expanded": "open",
                    "class": "w-full",
                    "tabindex": "0",
                    "role": "button",
                    "x-on:keydown.enter.prevent": "open = !open",
                    "x-on:keydown.space.prevent": "open = !open",
                },
                self.trigger,
            ),
            # Menu
            el(
                "div",
                {
                    "x-show": "open",
                    "x-transition:enter": "transition ease-out duration-100",
                    "x-transition:enter-start": "transform opacity-0 scale-95",
                    "x-transition:enter-end": "transform opacity-100 scale-100",
                    "x-transition:leave": "transition ease-in duration-75",
                    "x-transition:leave-start": "transform opacity-100 scale-100",
                    "x-transition:leave-end": "transform opacity-0 scale-95",
                    "class": f"absolute {origin_cls} {mt_cls} {origin_dir} z-50 w-full min-w-[14rem] rounded-md bg-popover text-popover-foreground shadow-lg ring-1 ring-border focus:outline-none",
                    "role": "menu",
                    "x-cloak": True,
                },
                el("div", {"class": "py-1", "role": "none"}, *menu_items),
            ),
        )
