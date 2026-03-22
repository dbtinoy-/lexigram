from __future__ import annotations

from typing import Any

from lexigram.ui import Component, NumberInput, Zones, el


class JumpToPage(Component):
    """
    Component for jumping to a specific page number.
    Uses Zone-based targeting for consistent HTMX behavior.
    """

    def __init__(
        self,
        page: int = 1,
        total_pages: int = 1,
        per_page: int = 20,
        base_url: str = "",
        extra_query: str = "",
        hx_target: str | None = None,
        hx_swap: str = "innerHTML",
        hx_push_url: str = "true",
        state: Any | None = None,
        **props,
    ) -> None:
        super().__init__(**props)
        self.page = page
        self.total_pages = total_pages
        self.per_page = per_page
        self.base_url = base_url
        self.extra_query = extra_query
        # Use Zones.DATA by default
        self.hx_target = hx_target or Zones.DATA.selector
        self.hx_swap = hx_swap
        self.hx_push_url = hx_push_url
        self.state = state

    def render(self) -> Any:
        # Build consistent HTMX attrs using new API

        if self.state:
            # Use clean URL with full state include to avoid duplication and state loss
            htmx_attrs = {
                "hx-get": f"{self.base_url.rstrip('/')}/",
                "hx-target": self.hx_target,
                "hx-swap": self.hx_swap,
                "hx-select": Zones.DATA.selector,
                "hx-push-url": "true",
                "hx-trigger": "change, keydown[key=='Enter']",
                "hx-include": f"{Zones.TABLE.selector} [name]",
                "hx-params": "*",
            }
        else:
            # Fallback for simple usage
            htmx_attrs = {
                "hx-get": f"{self.base_url}?per_page={self.per_page}{self.extra_query}",
                "hx-target": self.hx_target,
                "hx-swap": self.hx_swap,
                "hx-select": Zones.DATA.selector,
                "hx-push_url": str(self.hx_push_url).lower(),
                "hx-trigger": "change, keydown[key=='Enter']",
                "hx-include": "this",
            }

        return el(
            "div",
            el(
                "label",
                "Go to",
                class_="text-sm text-muted-foreground mr-2",
            ),
            NumberInput(
                name="page",
                label=None,
                value=self.page,
                min=1,
                max=self.total_pages,
                class_="w-16 text-center text-sm",
                **{k.replace("-", "_"): v for k, v in htmx_attrs.items()},  # type: ignore[arg-type]
            ),
            class_="flex items-center",
        )
