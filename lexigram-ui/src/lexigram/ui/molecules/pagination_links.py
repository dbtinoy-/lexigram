from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.ui import Component, Link, Zones, el

if TYPE_CHECKING:
    from lexigram.ui.state import TableState


class PaginationLinks(Component):
    """
    Component for rendering numeric page links and navigation buttons.
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
        state: TableState | None = None,
        **props,
    ) -> None:
        super().__init__(**props)
        self.page = page
        self.total_pages = total_pages
        self.per_page = per_page
        self.base_url = base_url
        self.extra_query = extra_query
        # Use Zones.DATA by default for pagination
        self.hx_target = hx_target or Zones.DATA.selector
        self.hx_swap = hx_swap
        self.hx_push_url = hx_push_url
        self.state = state

    def page_link(
        self,
        p: int,
        label: str | Any,
        disabled: bool = False,
        active: bool = False,
        extra_cls: str = "",
    ) -> Any:
        url = f"{self.base_url}?page={p}&per_page={self.per_page}{self.extra_query}"

        base_cls = "relative inline-flex items-center justify-center min-w-11 h-10 text-sm font-medium transition-colors focus:z-20 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-1"

        if disabled:
            return el(
                "span",
                label,
                class_=f"{base_cls} text-foreground dark:text-muted-foreground cursor-not-allowed bg-muted dark:bg-card {extra_cls}",
                **{"aria-disabled": "true"},
            )

        if active:
            # Active page: bold text with visible color using configured primary tokens
            cls = f"{base_cls} z-10 bg-primary text-primary-foreground font-bold border border-primary {extra_cls}"
        else:
            cls = f"{base_cls} text-foreground bg-card border border-border hover:bg-muted dark:hover:bg-muted {extra_cls}"

        # Build consistent HTMX attrs using new API
        from lexigram.ui import HTMXAttrs

        if self.state:
            # Generate "Baked URL" with all state params
            p_state = self.state.with_page(p)
            htmx_attrs = HTMXAttrs.for_data_refresh(
                state=p_state,
                resource_prefix=self.base_url.rstrip("/"),
                push_url=True,
            )
            url = htmx_attrs.get("hx-get", url)
        else:
            # Fallback for simple usage
            htmx_attrs = {
                "hx-get": url,
                "hx-trigger": "click",
                "hx-target": self.hx_target,
                "hx-swap": self.hx_swap,
                "hx-select": Zones.DATA.selector,
                "hx-push-url": str(self.hx_push_url).lower(),
                "hx-params": "none",
            }

        # Merge common navigation props
        attrs: dict[str, Any] = {
            "class_": cls,
            "onclick": "return false",
            "preload": "mouseover",
            **{k.replace("-", "_"): v for k, v in htmx_attrs.items()},
        }
        if active:
            attrs["aria-current"] = "page"
            # Remove HTMX from active page - no navigation needed
            for hx_attr in [
                "hx_get",
                "hx_trigger",
                "hx_target",
                "hx_swap",
                "hx_select",
                "hx_push_url",
                "hx_params",
                "preload",
            ]:
                attrs.pop(hx_attr, None)

            attrs["onclick"] = ""
            return el("span", label, **attrs)

        return Link(
            label,
            url,
            variant=("primary" if active else "default"),
            size="sm",
            **attrs,
        )

    def render(self) -> Any:
        from lexigram.ui import get_icon

        # Show first, last, current, and 1 page on each side of current
        show_pages = {1, self.total_pages, self.page, self.page - 1, self.page + 1}
        sorted_pages = sorted(
            filter(lambda p: 1 <= p <= self.total_pages, show_pages),
        )

        display_pages: list[int | str] = []
        last_p = 0
        for p in sorted_pages:
            if last_p > 0 and p - last_p > 1:
                if p - last_p > 2:
                    display_pages.append("...")
                else:
                    display_pages.append(last_p + 1)
            display_pages.append(p)
            last_p = p

        page_links = []
        for item in display_pages:
            if item == "...":
                page_links.append(
                    el(
                        "span",
                        "...",
                        class_="relative inline-flex items-center justify-center min-w-11 h-10 text-sm font-medium text-muted-foreground bg-card border-y border-border",
                    ),
                )
            else:
                page_links.append(
                    self.page_link(item, str(item), active=(item == self.page)),  # type: ignore[arg-type]
                )

        # Previous button with icon
        prev_icon = get_icon("chevron-left", size="h-4 w-4")
        prev_btn = self.page_link(
            self.page - 1,
            prev_icon,
            disabled=(self.page <= 1),
            extra_cls="rounded-l-lg border-r-0",
        )

        # Next button with icon
        next_icon = get_icon("chevron-right", size="h-4 w-4")
        next_btn = self.page_link(
            self.page + 1,
            next_icon,
            disabled=(self.page >= self.total_pages),
            extra_cls="rounded-r-lg border-l-0",
        )

        return el(
            "nav",
            prev_btn,
            *page_links,
            next_btn,
            class_="isolate inline-flex -space-x-px rounded-lg shadow-sm",
            **{"aria-label": "Pagination"},
        )
