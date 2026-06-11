"""Global search controller for lexigram-admin.

Provides the /admin/search endpoint consumed by the header search input
hx-get request and the CommandPalette component, and serves a full admin
page when the endpoint is navigated to directly (the Search nav item).
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
    (HTMX swaps) or as a full admin page on direct navigation.
    """

    def __init__(self, search_service: SearchService) -> None:
        self._search_service = search_service

    async def search(self, request: Request) -> HTMLResponse:
        """Handle GET /admin/search?q=... or ?search=... (plus optional ?rule=...)

        Args:
            request: Incoming HTTP request.

        Returns:
            HTMLResponse: an HTML fragment for HTMX requests (header search
                input and command palette), or a full admin page for direct
                navigation.
        """
        query = (
            request.query_params.get("q", "")
            or request.query_params.get("search", "")
            or ""
        )
        rule = request.query_params.get("rule") or None
        results = await self._search_service.search(query, rule=rule)
        fragment = self._render_results(results)

        if request.headers.get("hx-request") == "true":
            return HTMLResponse(fragment)
        return self._render_page(query, fragment, request, rule)

    def _render_page(
        self,
        query: str,
        fragment: str,
        request: Request,
        rule: str | None = None,
    ) -> HTMLResponse:
        """Render the search page inside the admin shell.

        The page embeds a search input (same HTMX wiring as the header) and a
        query-builder organism (block-JSON rule applied to indexed resources),
        plus a results container pre-filled with the current query's results,
        so a directly-navigated URL renders server-side and subsequent edits
        keep swapping into ``#search-results``.
        """
        from lexigram.admin.engine.renderer import AdminRenderer
        from lexigram.ui.core.base import el
        from lexigram.ui.organisms.query_builder import QueryBuilder

        catalog = self._search_service.get_search_field_catalog()
        builder = QueryBuilder(
            name="rule",
            value=rule,
            label="Filters",
            fields=catalog or None,
        )

        content = el(
            "div",
            el(
                "h1",
                "Global Search",
                class_="text-2xl font-bold mb-4 text-foreground",
            ),
            el(
                "form",
                el(
                    "div",
                    el(
                        "div",
                        el(
                            "input",
                            type="search",
                            name="q",
                            value=query or None,
                            placeholder="Search across resources…",
                            autocomplete="off",
                            hx_get="/admin/search",
                            hx_trigger="keyup changed delay:300ms",
                            hx_target="#search-results",
                            hx_include="#search-form",
                            class_="search-input w-full bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary",
                        ),
                        class_="relative",
                    ),
                    class_="mb-4",
                ),
                builder.render(),
                id="search-form",
                method="get",
                action="/admin/search",
                class_="mb-4",
            ),
            el(
                "div",
                fragment,
                id="search-results",
                class_="search-results-container",
            ),
            class_="p-6",
        )
        return AdminRenderer().render_page(
            content,
            request=request,
            title="Global Search",
            breadcrumbs=[{"label": "Search", "url": "/admin/search"}],
        )

    def _render_results(self, results: SearchResults) -> str:
        """Render search results as an HTML fragment.

        When results are present the output is grouped by resource with
        a header per group.  When no results match a simple "no results"
        placeholder is returned.
        """
        if not results.has_results:
            return (
                '<div class="search-results-empty '
                "text-center py-8 px-4 text-sm text-muted-foreground dark:text-muted-foreground"
                '">No results found</div>'
            )

        sections: list[str] = []
        count_text = f"{results.total_count} result{'s' if results.total_count != 1 else ''} across {results.group_count} resource{'s' if results.group_count != 1 else ''}"
        sections.append(
            '<div class="search-summary px-4 py-2 text-xs text-muted-foreground border-b border-border/50">'
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
                    f"hover:bg-muted dark:hover:bg-muted/50 "
                    f"focus:bg-muted "
                    f'focus:outline-none transition-colors" '
                    f'hx-get="{r.url}" hx-target="body" hx-push-url="true">'
                    f'<span class="search-result-title '
                    f"block text-sm font-medium text-foreground"
                    f'">{r.title}</span>'
                    f"{subtitle_html}"
                    f'<span class="search-result-resource '
                    f"inline-block text-xs text-muted-foreground dark:text-muted-foreground mt-0.5"
                    f'">{resource_label}</span>'
                    f"</a>"
                )

            sections.append(
                '<div class="search-resource-group '
                "border-b border-border/50 last:border-b-0"
                '">'
                f'<div class="search-resource-header '
                f"px-4 py-2 text-xs font-semibold uppercase tracking-wider "
                f"text-muted-foreground dark:text-muted-foreground "
                f"bg-muted dark:bg-card/50"
                f'">{resource_label}</div>'
                f"{items_html}"
                "</div>"
            )

        return (
            '<div class="search-results '
            "rounded-xl shadow-lg bg-card "
            "overflow-hidden max-h-[70vh] overflow-y-auto"
            '">' + "".join(sections) + "</div>"
        )


__all__ = ["SearchController"]
