from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.serialization import dumps_str
from lexigram.ui import Component, HTMXAttrs, Zones, el

CONTROL_SELECT_CLASSES = (
    "px-2 py-1.5 h-8 border rounded text-sm bg-card dark:border-border"
)

if TYPE_CHECKING:
    from lexigram.ui.state import TableState


class TablePagination(Component):
    """Pagination component with HTMX support and baked URL pattern.

    Supports two modes:
    1. State-based (recommended): Pass a TableState for baked URLs
    2. Legacy: Pass page/total/per_page directly
    """

    def __init__(
        self,
        page: int = 1,
        total: int = 0,
        per_page: int = 20,
        base_url: str = "",
        state: TableState | None = None,
        show_size_selector: bool = True,
        **props: Any,
    ) -> None:
        super().__init__()
        self.state = state
        # If state provided, extract values from it
        if state:
            self.page = max(1, int(state.page))
            self.per_page = max(1, int(state.per_page))
        else:
            self.page = max(1, int(page))
            self.per_page = max(1, int(per_page))
        self.total = max(0, int(total))
        self.base_url = base_url
        self.show_size_selector = show_size_selector

    def render(self) -> Any:
        if self.total <= self.per_page:
            return ""

        start = (self.page - 1) * self.per_page + 1
        end = min(self.total, self.page * self.per_page)
        total_pages = (self.total + self.per_page - 1) // self.per_page

        # Summary
        summary = el(
            "div",
            f"Showing {start} to {end} of {self.total}",
            class_="text-sm text-muted-foreground",
        )

        # Build links
        links = []

        # Previous control
        if self.page > 1:
            links.append(self._page_link(self.page - 1, "Prev"))
        else:
            links.append(
                el(
                    "span",
                    "Prev",
                    class_="px-2 py-1 text-sm text-muted-foreground cursor-not-allowed",
                ),
            )

        # Page numbers (with ellipsis for large page counts)
        visible_pages = self._get_visible_pages(self.page, total_pages)
        for p in visible_pages:
            if p is None:
                links.append(
                    el("span", "...", class_="px-2 py-1 text-sm text-muted-foreground"),
                )
            elif p == self.page:
                # Current page: bold text with visible color (not white)
                links.append(
                    el(
                        "span",
                        str(p),
                        class_="px-2 py-1 text-sm font-bold text-foreground",
                    ),
                )
            else:
                links.append(self._page_link(p, str(p)))

        # Next control
        if self.page < total_pages:
            links.append(self._page_link(self.page + 1, "Next"))
        else:
            links.append(
                el(
                    "span",
                    "Next",
                    class_="px-2 py-1 text-sm text-muted-foreground cursor-not-allowed",
                ),
            )

        # Size selector (optional)
        size_selector = ""
        if self.show_size_selector:
            size_options = [10, 25, 50, 100]
            size_items = [
                el(
                    "option",
                    str(size),
                    value=str(size),
                    selected="selected" if size == self.per_page else None,
                )
                for size in size_options
            ]

            # Build HTMX attrs for size change
            size_attrs = self._get_size_change_attrs()

            size_selector = el(
                "div",
                el(
                    "label",
                    "Show",
                    class_="mr-2 text-sm text-muted-foreground",
                ),
                el(
                    "select",
                    *size_items,
                    name="per_page",
                    class_=CONTROL_SELECT_CLASSES,
                    **size_attrs,
                ),
                class_="ml-4 flex items-center",
            )

        return el(
            "div",
            summary,
            el("div", *links, class_="mt-2 space-x-1"),
            size_selector,
            class_="pagination flex flex-wrap items-center gap-4",
        )

    def _page_link(self, page_num: int, label: str) -> Any:
        """Generate a page link with correct HTMX attributes."""
        if self.state:
            updated_state = self.state.with_page(page_num)
            attrs = HTMXAttrs.for_data_refresh(
                updated_state,
                self.base_url,
                push_url=True,
            )
            # Convert hx-* to hx_* for element builder
            el_attrs = {k.replace("-", "_"): v for k, v in attrs.items()}
        else:
            # Legacy mode fallback
            el_attrs = {
                "href": f"{self.base_url}?page={page_num}&per_page={self.per_page}",
                "hx_get": f"{self.base_url}?page={page_num}&per_page={self.per_page}",
                "hx_target": Zones.DATA.selector,
                "hx_swap": "outerHTML",
                "hx_select": Zones.DATA.selector,
                "hx_select_oob": Zones.data_refresh_oob_select(),
                "hx_push_url": "true",
            }

        return el(
            "a",
            label,
            **el_attrs,
            class_="px-2 py-1 text-sm text-primary-600 hover:underline dark:text-primary-400 cursor-pointer",
        )

    def _get_size_change_attrs(self) -> dict[str, str]:
        """Get HTMX attrs for the size selector."""
        if self.state:
            params = self.state.to_query_params()
            params.pop("per_page", None)
            params.pop("page", None)
            params.pop("cursor", None)
            base_url = self.base_url.rstrip("/")
            return {
                "hx_get": base_url,
                "hx_target": Zones.DATA.selector,
                "hx_select": Zones.DATA.selector,
                "hx_select_oob": Zones.data_refresh_oob_select(),
                "hx_swap": "outerHTML",
                "hx_trigger": "change",
                "hx_vals": dumps_str(params),
                "hx_push_url": "true",
            }
        return {
            "hx_get": self.base_url,
            "hx_target": Zones.DATA.selector,
            "hx_swap": "outerHTML",
            "hx_trigger": "change",
        }

    def _get_visible_pages(
        self,
        current: int,
        total: int,
        window: int = 2,
    ) -> list[int | None]:
        """Get list of page numbers to display, with None for ellipsis."""
        if total <= 7:
            return list(range(1, total + 1))

        pages: list[int | None] = []

        # Always show first page
        pages.append(1)

        # Show ellipsis if current is far from start
        if current > window + 2:
            pages.append(None)

        # Show pages around current
        start = max(2, current - window)
        end = min(total - 1, current + window)

        for p in range(start, end + 1):
            if p not in pages:
                pages.append(p)

        # Show ellipsis if current is far from end
        if current < total - window - 1:
            pages.append(None)

        # Always show last page
        if total not in pages:
            pages.append(total)

        return pages
