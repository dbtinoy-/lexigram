from __future__ import annotations

from typing import Any

from lexigram.ui import (
    Component,
    JumpToPage,
    Link,
    PageSizeSelector,
    PaginationLinks,
    Zones,
    el,
)


class Pagination(Component):
    """
    Standalone pagination component with page size selector and jump to page.
    Compiles molecules into a functional organism.
    Uses Zone-based targeting for consistent HTMX behavior.
    """

    def __init__(
        self,
        page: int = 1,
        total: int = 0,
        per_page: int = 20,
        base_url: str = "",
        show_size_selector: bool = True,
        show_jump_to_page: bool = True,
        extra_query: str = "",
        hx_target: str | None = None,
        hx_swap: str = "innerHTML",
        hx_push_url: str = "true",
        next_cursor: str | None = None,
        state: Any | None = None,
        **props,
    ) -> None:
        super().__init__(
            page=page,
            total=total,
            per_page=per_page,
            base_url=base_url,
            **props,
        )
        self.state = state
        self.page = max(1, int(page))
        self.total = max(0, int(total))
        self.per_page = max(1, int(per_page))
        self.base_url = base_url
        self.next_cursor = next_cursor
        self.show_size_selector = show_size_selector
        self.show_jump_to_page = show_jump_to_page
        self.extra_query = extra_query
        # Use Zones.DATA by default
        self.hx_target = hx_target or Zones.DATA.selector
        self.hx_swap = hx_swap
        self.hx_push_url = hx_push_url

    def render(self) -> Any:
        if self.total <= 0:
            return ""

        total_pages = (self.total + self.per_page - 1) // self.per_page

        start_item = (self.page - 1) * self.per_page + 1
        end_item = min(self.page * self.per_page, self.total)

        # Render Modular Components
        size_selector = (
            PageSizeSelector(
                per_page=self.per_page,
                base_url=self.base_url,
                extra_query=self.extra_query,
                hx_target=self.hx_target,
                hx_swap=self.hx_swap,
                hx_push_url=self.hx_push_url,
                state=self.state,
            )
            if self.show_size_selector
            else ""
        )

        jump_to_page = (
            JumpToPage(
                page=self.page,
                total_pages=total_pages,
                per_page=self.per_page,
                base_url=self.base_url,
                extra_query=self.extra_query,
                hx_target=self.hx_target,
                hx_swap=self.hx_swap,
                hx_push_url=self.hx_push_url,
                state=self.state,
            )
            if self.show_jump_to_page
            else ""
        )

        page_links = PaginationLinks(
            page=self.page,
            total_pages=total_pages,
            per_page=self.per_page,
            base_url=self.base_url,
            extra_query=self.extra_query,
            hx_target=self.hx_target,
            hx_swap=self.hx_swap,
            hx_push_url=self.hx_push_url,
            state=self.state,
        )

        return el(
            "div",
            {
                "id": "table-pagination",
                "class": "flex items-center justify-between border-t border-border bg-background px-4 py-3 mt-4",
            },
            # Mobile View
            el(
                "div",
                {"class": "flex flex-1 justify-between sm:hidden"},
                # Previous (mobile). Render as span when disabled to avoid HTMX attributes on inactive controls.
                (
                    el(
                        "span",
                        "Previous",
                        class_=f"relative inline-flex items-center rounded-md border border-border bg-card px-4 py-2 text-sm font-medium text-foreground {'invisible' if self.page <= 1 else ''}",
                    )
                    if self.page <= 1
                    else Link(
                        "Previous",
                        f"{self.base_url}?page={max(1, self.page - 1)}&per_page={self.per_page}{self.extra_query}",
                        color="muted",
                        class_=f"relative inline-flex items-center rounded-md border border-border bg-card px-4 py-2 text-sm font-medium text-foreground hover:bg-muted {'invisible' if self.page <= 1 else ''}",
                        hx_get=f"{self.base_url}?page={max(1, self.page - 1)}&per_page={self.per_page}{self.extra_query}",
                        hx_trigger="click",
                        hx_target=self.hx_target,
                        hx_swap=self.hx_swap,
                        hx_push_url=self.hx_push_url,
                        hx_include="this",
                        onclick="return false",
                        preload="mouseover",
                    )
                ),
                # Next (mobile). Render as span when disabled to avoid HTMX attributes on inactive controls.
                (
                    el(
                        "span",
                        "Next",
                        class_=f"relative ml-3 inline-flex items-center rounded-md border border-border bg-card px-4 py-2 text-sm font-medium text-foreground {'invisible' if not self.next_cursor and self.page >= total_pages else ''}",
                    )
                    if (not self.next_cursor and self.page >= total_pages)
                    else Link(
                        "Next",
                        f"{self.base_url}?cursor={self.next_cursor}&per_page={self.per_page}{self.extra_query}"
                        if self.next_cursor
                        else f"{self.base_url}?page={min(total_pages, self.page + 1)}&per_page={self.per_page}{self.extra_query}",
                        class_=f"relative ml-3 inline-flex items-center rounded-md border border-border bg-card px-4 py-2 text-sm font-medium text-foreground hover:bg-muted {'invisible' if not self.next_cursor and self.page >= total_pages else ''}",
                        hx_get=f"{self.base_url}?cursor={self.next_cursor}&per_page={self.per_page}{self.extra_query}"
                        if self.next_cursor
                        else f"{self.base_url}?page={min(total_pages, self.page + 1)}&per_page={self.per_page}{self.extra_query}",
                        hx_trigger="click",
                        hx_target=self.hx_target,
                        hx_swap=self.hx_swap,
                        hx_push_url=self.hx_push_url,
                        hx_include="this",
                        onclick="return false",
                        preload="mouseover",
                    )
                ),
            ),
            # Desktop View
            el(
                "div",
                {
                    "class": "hidden sm:flex sm:flex-1 sm:items-center sm:justify-between px-4",
                },
                # Results text
                el(
                    "div",
                    el(
                        "p",
                        "Showing ",
                        el("span", str(start_item), class_="font-bold"),
                        " to ",
                        el("span", str(end_item), class_="font-bold"),
                        " of ",
                        el("span", str(self.total), class_="font-bold"),
                        " results",
                        class_="text-[11px] uppercase tracking-wider text-muted-foreground font-semibold",
                    ),
                ),
                # Pagination Controls
                el(
                    "div",
                    page_links,
                    size_selector,
                    jump_to_page,
                    class_="flex items-center space-x-4",
                ),
            ),
        )
