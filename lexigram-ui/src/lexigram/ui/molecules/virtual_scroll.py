"""Virtual Scroll component for Lexigram Admin."""

from __future__ import annotations

from typing import Any

from lexigram.ui.core.base import Component, el


class VirtualScroll(Component):
    """Component for handling infinite scroll and virtualization.

    This uses HTMX 'revealed' trigger to load next chunks of data.
    """

    def __init__(
        self,
        url: str,
        total_items: int | None = None,
        chunk_size: int = 50,
        target_id: str | None = None,
        placeholder: Any | None = None,
        **props,
    ):
        super().__init__(**props)
        self.url = url
        self.total_items = total_items
        self.chunk_size = chunk_size
        self.target_id = target_id
        self.placeholder = placeholder

    def render(self) -> Any:
        return el(
            "div",
            self.children,
            id=self.target_id or "virtual-scroll-container",
            class_="virtual-scroll",
            **self.props,
        )


def render_infinite_row(
    row_content: Any,
    next_url: str | None = None,
    trigger: str = "revealed",
    threshold: str = "0.5",
) -> Any:
    """Helper to render a row that triggers the next page load.

    Args:
        row_content: The content of the current row
        next_url: URL to fetch the next page. If None, no trigger is added.
        trigger: HTMX trigger (default 'revealed')
        threshold: Intersection observer threshold
    """
    if not next_url:
        return row_content

    attrs = {
        "hx-get": next_url,
        "hx-trigger": f"{trigger} threshold:{threshold}",
        "hx-swap": "afterend",
    }

    if hasattr(row_content, "attrs"):
        row_content.attrs.update(attrs)
        return row_content

    return el("div", row_content, **attrs)


class InfiniteScrollTrigger(Component):
    """A component that triggers an HTMX request when scrolled into view."""

    def __init__(
        self,
        url: str,
        trigger: str = "revealed",
        target: str | None = None,
        swap: str = "afterend",
        select: str | None = None,
        **props,
    ):
        super().__init__(**props)
        self.url = url
        self.trigger = trigger
        self.target = target
        self.swap = swap
        self.select = select or "#table-content > *"

    def render(self) -> Any:
        children = self.children or [
            el(
                "div",
                el(
                    "i",
                    class_="fas fa-spinner fa-spin mr-2 text-primary",
                ),
                el("span", "Loading more...", class_="text-muted-foreground text-sm"),
                class_="flex items-center justify-center p-4 w-full",
            ),
        ]

        return el(
            "div",
            *children,
            **{
                "hx-get": self.url,
                "hx-trigger": self.trigger,
                "hx-target": self.target,
                "hx-swap": self.swap,
                "hx-select": self.select,
                **self.props,
            },
        )
