from __future__ import annotations

from typing import Any

from lexigram.ui import Component, Select, Zones, el


class PageSizeSelector(Component):
    """
    Component for selecting the number of items per page.
    Uses Zone-based targeting for consistent HTMX behavior.
    """

    def __init__(
        self,
        per_page: int = 20,
        base_url: str = "",
        extra_query: str = "",
        hx_target: str | None = None,
        hx_swap: str = "innerHTML",
        hx_push_url: str = "true",
        size_options: list[int] | None = None,
        state: Any | None = None,
        **props,
    ) -> None:
        super().__init__(**props)
        self.per_page = per_page
        self.base_url = base_url
        self.extra_query = extra_query
        # Use Zones.DATA by default
        self.hx_target = hx_target or Zones.DATA.selector
        self.hx_swap = hx_swap
        self.hx_push_url = hx_push_url
        self.size_options = size_options or [10, 20, 50, 100]
        self.state = state

    def render(self) -> Any:
        choices = [(str(size), str(size)) for size in self.size_options]

        # Build consistent HTMX attrs using new API

        if self.state:
            # Use clean URL with full state include to avoid duplication and state loss
            htmx_attrs = {
                "hx-get": f"{self.base_url.rstrip('/')}/",
                "hx-target": self.hx_target,
                "hx-swap": self.hx_swap,
                "hx-select": Zones.DATA.selector,
                "hx-push_url": "true",
                "hx-trigger": "change",
                "hx-include": f"{Zones.TABLE.selector} [name]",
                "hx-params": "*",
            }
        else:
            # Fallback for simple usage
            htmx_attrs = {
                "hx-get": f"{self.base_url}?page=1{self.extra_query}",
                "hx-target": self.hx_target,
                "hx-swap": self.hx_swap,
                "hx-select": Zones.DATA.selector,
                "hx-push_url": str(self.hx_push_url).lower(),
                "hx-trigger": "change",
                "hx-include": "this",
            }

        return el(
            "div",
            el(
                "label",
                "per page",
                class_="text-sm text-muted-foreground mr-2 hidden lg:inline",
            ),
            Select(
                name="per_page",
                label=None,
                choices=choices,
                value=str(self.per_page),
                class_="w-20 text-sm",
                **{k.replace("-", "_"): v for k, v in htmx_attrs.items()},  # type: ignore[arg-type]
            ),
            class_="flex items-center",
        )
