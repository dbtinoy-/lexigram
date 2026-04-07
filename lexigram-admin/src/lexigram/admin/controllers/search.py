"""Global search controller for lexigram-admin.

Provides the /admin/search endpoint consumed by the header search input
hx-get request and the CommandPalette component.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from starlette.responses import HTMLResponse

if TYPE_CHECKING:
    from starlette.requests import Request

    from lexigram.admin.services.search_service import SearchResults, SearchService


class SearchController:
    """Controller for the global search endpoint.

    Accepts a query via ``?q=...`` or ``?search=...``, delegates to
    SearchService, and renders the aggregated results as HTML fragments
    suitable for HTMX swap.
    """

    def __init__(self, search_service: SearchService) -> None:
        self._search_service = search_service

    async def search(self, request: Request) -> HTMLResponse:
        """Handle GET /admin/search?q=... or ?search=...

        Args:
            request: Incoming HTTP request.

        Returns:
            HTMLResponse with rendered search results.
        """
        query = (
            request.query_params.get("q", "")
            or request.query_params.get("search", "")
            or ""
        )
        results = await self._search_service.search(query)
        html = self._render_results(results)
        return HTMLResponse(html)

    def _render_results(self, results: SearchResults) -> str:
        """Render search results as an HTML fragment.

        When results are present the output is grouped by resource with
        a header per group.  When no results match a simple "no results"
        placeholder is returned.
        """
        if not results.has_results:
            return (
                '<div class="search-results-empty '
                "text-center py-8 px-4 text-sm text-gray-500 dark:text-gray-400"
                '">No results found</div>'
            )

        sections: list[str] = []
        count_text = f"{results.total_count} result{'s' if results.total_count != 1 else ''} across {results.group_count} resource{'s' if results.group_count != 1 else ''}"
        sections.append(
            '<div class="search-summary px-4 py-2 text-xs text-gray-400 dark:text-gray-500 border-b border-gray-100 dark:border-gray-700/50">'
            f"{count_text}"
            "</div>"
        )
        for resource_name in results.resource_counts:
            resource_label: str = ""
            for r in results.results:
                if r.resource_name == resource_name:
                    resource_label = r.resource_label
                    break

            items_html = ""
            for r in results.results:
                if r.resource_name != resource_name:
                    continue
                subtitle_html = (
                    f'<span class="search-subtitle">{r.subtitle}</span>'
                    if r.subtitle
                    else ""
                )
                items_html += (
                    f'<a href="{r.url}" '
                    f'class="search-result-item '
                    f"block px-4 py-3 "
                    f"hover:bg-gray-50 dark:hover:bg-gray-700/50 "
                    f"focus:bg-blue-50 dark:focus:bg-blue-900/20 "
                    f'focus:outline-none transition-colors" '
                    f'hx-get="{r.url}" hx-target="body" hx-push-url="true">'
                    f'<span class="search-result-title '
                    f"block text-sm font-medium text-gray-900 dark:text-gray-100"
                    f'">{r.title}</span>'
                    f"{subtitle_html}"
                    f'<span class="search-result-resource '
                    f"inline-block text-xs text-gray-400 dark:text-gray-500 mt-0.5"
                    f'">{resource_label}</span>'
                    f"</a>"
                )

            sections.append(
                '<div class="search-resource-group '
                "border-b border-gray-100 dark:border-gray-700/50 last:border-b-0"
                '">'
                f'<div class="search-resource-header '
                f"px-4 py-2 text-xs font-semibold uppercase tracking-wider "
                f"text-gray-500 dark:text-gray-400 "
                f"bg-gray-50 dark:bg-gray-800/50"
                f'">{resource_label}</div>'
                f"{items_html}"
                "</div>"
            )

        return (
            '<div class="search-results '
            "rounded-xl shadow-lg bg-white dark:bg-gray-800 "
            "overflow-hidden max-h-[70vh] overflow-y-auto"
            '">' + "".join(sections) + "</div>"
        )


__all__ = ["SearchController"]
