"""Host-side renderer for structured management page content.

``PageContent`` is the only way management pages reach the browser. This module
builds the page shell (header + body + pagination) via ``lexigram-ui``; the body
is rendered by ``render_content`` exactly like dashboard widgets.
"""

from __future__ import annotations

from starlette.responses import HTMLResponse

from lexigram.admin.dashboard.content_renderer import render_content
from lexigram.contracts.admin.page_content import PageContent, PaginationContent
from lexigram.ui import PageSizeSelector, PaginationLinks, el, raw, render_to_string


def _render_pagination(pagination: PaginationContent) -> str:
    """Render the "Showing X to Y of Z" block + pager + page-size selector."""
    total = pagination.total
    if total <= 0:
        return ""
    total_pages = max(1, (total + pagination.per_page - 1) // pagination.per_page)
    start_item = (pagination.page - 1) * pagination.per_page + 1
    end_item = min(pagination.page * pagination.per_page, total)
    return render_to_string(
        el(
            "div",
            {
                "class": (
                    "flex items-center justify-between border-t border-border "
                    "bg-background px-4 py-3 mt-4"
                ),
            },
            el(
                "p",
                {
                    "class": (
                        "text-[11px] uppercase tracking-wider "
                        "text-[var(--muted-foreground)] font-semibold"
                    ),
                },
                "Showing ",
                el("span", {"class": "font-bold"}, str(start_item)),
                " to ",
                el("span", {"class": "font-bold"}, str(end_item)),
                " of ",
                el("span", {"class": "font-bold"}, str(total)),
                " results",
            ),
            el(
                "div",
                {"class": "flex items-center space-x-4"},
                PaginationLinks(
                    page=pagination.page,
                    total_pages=total_pages,
                    per_page=pagination.per_page,
                    base_url=pagination.base_url,
                ),
                PageSizeSelector(
                    per_page=pagination.per_page,
                    base_url=pagination.base_url,
                ),
            ),
        )
    )


def render_page_content(content: PageContent) -> HTMLResponse:
    """Render structured page content to an HTML response."""
    body_html = render_content(content.body)
    pagination_html = (
        _render_pagination(content.pagination) if content.pagination else ""
    )
    html = render_to_string(
        el(
            "div",
            {"class": "space-y-6"},
            el(
                "h1",
                {"class": "text-2xl font-semibold tracking-tight"},
                content.title,
            ),
            el(
                "div",
                {"id": "table-data"},
                raw(body_html),
                raw(pagination_html),
            ),
        )
    )
    return HTMLResponse(html)
