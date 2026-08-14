"""Simple general-purpose prev/next pagination component."""

from __future__ import annotations

from typing import Any

from lexigram.ui.core.base import Component, el


class Pagination(Component):
    """Simple prev/next pagination for any URL-based page navigation.

    Renders summary text and previous/next page links using plain anchor tags.
    For HTMX-enhanced pagination with zone targeting, use the admin-specific
    Pagination in lexigram.admin.ui.
    """

    def __init__(
        self,
        page: int = 1,
        total: int = 0,
        per_page: int = 20,
        base_url: str = "",
        show_summary: bool = True,
        **props: Any,
    ) -> None:
        """Initialize the pagination component.

        Args:
            page: Current page number (1-based).
            total: Total number of items.
            per_page: Number of items per page.
            base_url: Base URL for page links (page/per_page appended as query params).
            show_summary: Whether to show the "Showing X to Y of Z" summary.
        """
        super().__init__()
        self.page = max(1, int(page))
        self.total = max(0, int(total))
        self.per_page = max(1, int(per_page))
        self.base_url = base_url
        self.show_summary = show_summary

    @property
    def total_pages(self) -> int:
        """Total number of pages."""
        return (self.total + self.per_page - 1) // self.per_page

    def _page_url(self, page: int) -> str:
        separator = "&" if "?" in self.base_url else "?"
        return f"{self.base_url}{separator}page={page}&per_page={self.per_page}"

    def render(self) -> Any:
        if self.total_pages <= 1:
            return ""

        start = (self.page - 1) * self.per_page + 1
        end = min(self.total, self.page * self.per_page)

        parts: list[Any] = []

        if self.show_summary:
            parts.append(
                el(
                    "span",
                    f"Showing {start}-{end} of {self.total}",
                    class_="text-sm text-muted-foreground",
                ),
            )

        if self.page > 1:
            parts.append(
                el(
                    "a",
                    "← Previous",
                    href=self._page_url(self.page - 1),
                    class_="px-3 py-1 text-sm text-primary hover:underline",
                    aria_label="Previous page",
                ),
            )
        else:
            parts.append(
                el(
                    "span",
                    "← Previous",
                    class_="px-3 py-1 text-sm text-muted-foreground cursor-not-allowed",
                ),
            )

        parts.append(
            el(
                "span",
                f"Page {self.page} of {self.total_pages}",
                class_="px-3 py-1 text-sm text-foreground",
                aria_current="page",
            ),
        )

        if self.page < self.total_pages:
            parts.append(
                el(
                    "a",
                    "Next →",
                    href=self._page_url(self.page + 1),
                    class_="px-3 py-1 text-sm text-primary hover:underline",
                    aria_label="Next page",
                ),
            )
        else:
            parts.append(
                el(
                    "span",
                    "Next →",
                    class_="px-3 py-1 text-sm text-muted-foreground cursor-not-allowed",
                ),
            )

        return el(
            "nav",
            *parts,
            class_="flex flex-wrap items-center gap-2",
            aria_label="Pagination",
        )


__all__ = ["Pagination"]
