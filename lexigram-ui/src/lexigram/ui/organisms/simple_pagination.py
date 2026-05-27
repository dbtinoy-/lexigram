"""Simple pagination component — no COUNT query required.

Provides ``SimplePagination`` which renders only Previous/Next navigation
without a total page count.  This is a critical performance optimisation
for large tables where ``COUNT(*)`` is expensive (React Admin Y).

The component uses a ``has_next_page`` boolean (set from the data layer
by fetching ``per_page + 1`` rows and checking if the extra row exists)
instead of a total count.

Usage::

    rows = await db.fetch(limit=per_page + 1, offset=offset)
    has_next = len(rows) > per_page
    rows = rows[:per_page]

    pager = SimplePagination(
        page=2,
        per_page=25,
        has_next_page=has_next,
        base_url="/admin/users",
    )
"""

from __future__ import annotations

from typing import Any

from lexigram.ui import Component, el


class SimplePagination(Component):
    """Prev / Next pagination with no total-count requirement.

    Renders only a "Previous" button and a "Next" button, enabling
    fast pagination without an expensive ``COUNT(*)`` query.

    Args:
        page: Current (1-based) page number.
        per_page: Items per page.
        has_next_page: Whether a next page exists.  Set this by fetching
            ``per_page + 1`` rows and checking if more than ``per_page``
            were returned.
        base_url: Base URL for page links.
        extra_query: Additional query string parameters to append (without
            leading ``&``).
        hx_target: HTMX target selector (default ``#main-content``).
        hx_push_url: Whether HTMX should push the URL (default ``"true"``).
    """

    def __init__(
        self,
        page: int = 1,
        per_page: int = 20,
        has_next_page: bool = False,
        base_url: str = "",
        extra_query: str = "",
        hx_target: str = "#main-content",
        hx_push_url: str = "true",
        **props: Any,
    ) -> None:
        super().__init__(**props)
        self.page = page
        self.per_page = per_page
        self.has_next_page = has_next_page
        self.base_url = base_url.rstrip("/")
        self.extra_query = f"&{extra_query}" if extra_query else ""
        self.hx_target = hx_target
        self.hx_push_url = hx_push_url

    def render(self) -> Any:
        has_prev = self.page > 1
        prev_url = self._page_url(self.page - 1)
        next_url = self._page_url(self.page + 1)

        prev_btn = self._nav_button(
            label="← Previous",
            url=prev_url,
            enabled=has_prev,
        )
        next_btn = self._nav_button(
            label="Next →",
            url=next_url,
            enabled=self.has_next_page,
        )
        page_label = el(
            "span",
            f"Page {self.page}",
            class_="text-sm text-muted-foreground px-3",
        )

        return el(
            "nav",
            prev_btn,
            page_label,
            next_btn,
            class_=(
                "flex items-center justify-between gap-2 py-3 border-t border-border"
            ),
            **{"aria-label": "Pagination"},
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _page_url(self, page: int) -> str:
        base = self.base_url or "."
        return f"{base}?page={page}&per_page={self.per_page}{self.extra_query}"

    def _nav_button(self, label: str, url: str, enabled: bool) -> Any:
        disabled_cls = "opacity-50 cursor-not-allowed pointer-events-none"
        enabled_cls = "hover:bg-muted dark:hover:bg-muted"
        base_cls = (
            "inline-flex items-center px-4 py-2 text-sm font-medium rounded-md "
            "border border-border "
            "bg-card "
            "text-foreground "
            "transition-colors"
        )
        extra_cls = enabled_cls if enabled else disabled_cls

        attrs: dict[str, Any] = {
            "class": f"{base_cls} {extra_cls}",
        }
        if enabled:
            attrs.update(
                {
                    "href": url,
                    "hx-get": url,
                    "hx-target": self.hx_target,
                    "hx-push-url": self.hx_push_url,
                }
            )

        tag = "a" if enabled else "span"
        return el(tag, label, **attrs)
