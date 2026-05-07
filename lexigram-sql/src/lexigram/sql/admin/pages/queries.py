from __future__ import annotations

from typing import Any

from starlette.responses import HTMLResponse

from lexigram.contracts.data.sql.query_log import QueryLoggerProtocol
from lexigram.logging import get_logger
from lexigram.ui import (
    Divider,
    EmptyState,
    PageSizeSelector,
    PaginationLinks,
    Zones,
    el,
    render_to_string,
)

logger = get_logger(__name__)

DEFAULT_PER_PAGE = 20
MAX_PER_PAGE = 200


def _query_int(request: Any, name: str, default: int, lo: int, hi: int) -> int:
    try:
        value = int(request.query_params.get(name, default))
    except (TypeError, ValueError):
        value = default
    return max(lo, min(value, hi))


def _paging(request: Any) -> tuple[int, int]:
    page = _query_int(request, "page", 1, 1, 10**6)
    per_page = _query_int(request, "per_page", DEFAULT_PER_PAGE, 1, MAX_PER_PAGE)
    return page, per_page


def _pagination_block(page: int, total: int, per_page: int, base_url: str) -> Any:
    if total <= 0:
        return ""
    total_pages = max(1, (total + per_page - 1) // per_page)
    start_item = (page - 1) * per_page + 1
    end_item = min(page * per_page, total)
    return el(
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
                page=page,
                total_pages=total_pages,
                per_page=per_page,
                base_url=base_url,
            ),
            PageSizeSelector(per_page=per_page, base_url=base_url),
        ),
    )


class SqlQueriesPage:
    def __init__(
        self,
        query_logger: QueryLoggerProtocol | None = None,
    ) -> None:
        self._query_logger = query_logger

    async def handle(self, request: Any) -> HTMLResponse:
        if self._query_logger is None:
            html = render_to_string(
                EmptyState(
                    title="Query Logging Disabled",
                    message="No query logger is configured. Enable query logging to see recent queries.",
                    icon="search",
                ),
            )
            return HTMLResponse(html)

        try:
            entries = await self._query_logger.get_recent_queries(limit=10_000)
        except Exception:
            html = render_to_string(
                EmptyState(
                    title="Error",
                    message="Failed to load recent queries. Check the server logs for details.",
                    icon="alert-triangle",
                ),
            )
            return HTMLResponse(html)

        if not entries:
            html = render_to_string(
                EmptyState(
                    title="No Queries",
                    message="No queries have been logged yet.",
                    icon="search",
                ),
            )
            return HTMLResponse(html)

        page, per_page = _paging(request)
        total = len(entries)
        page = min(page, max(1, (total + per_page - 1) // per_page))
        offset = (page - 1) * per_page
        page_entries = entries[offset : offset + per_page]

        rows = "".join(
            render_to_string(
                el(
                    "tr",
                    el(
                        "td",
                        (m.sql[:80] + "..." if len(m.sql) > 80 else m.sql),
                        class_="px-4 py-3 whitespace-nowrap text-sm font-mono text-[var(--foreground)]",
                    ),
                    el(
                        "td",
                        f"{int(m.execution_time * 1000)}ms",
                        class_="px-4 py-3 whitespace-nowrap text-sm",
                    ),
                    el(
                        "td",
                        m.timestamp.isoformat() if m.timestamp else "",
                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--muted-foreground)]",
                    ),
                )
            )
            for m in page_entries
        )

        html = render_to_string(
            el(
                "div",
                el(
                    "h1",
                    "Recent Queries",
                    class_="text-2xl font-bold text-[var(--foreground)]",
                ),
                el(
                    "p",
                    "View recent SQL queries executed against the database.",
                    class_="text-sm text-[var(--muted-foreground)] mt-1 mb-6",
                ),
                Divider(),
                el(
                    "div",
                    el(
                        "div",
                        el(
                            "table",
                            el(
                                "thead",
                                el(
                                    "tr",
                                    el(
                                        "th",
                                        "Query",
                                        style="width:50%",
                                        class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                    ),
                                    el(
                                        "th",
                                        "Duration",
                                        style="width:20%",
                                        class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                    ),
                                    el(
                                        "th",
                                        "Timestamp",
                                        style="width:30%",
                                        class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                    ),
                                ),
                            ),
                            el("tbody", rows, class_="divide-y divide-[var(--border)]"),
                            class_="min-w-full table-fixed divide-y divide-[var(--border)]",
                        ),
                        class_="overflow-x-auto rounded-xl border border-[var(--border)] bg-[var(--card)]",
                    ),
                    _pagination_block(page, total, per_page, request.url.path),
                    id=Zones.DATA.id,
                ),
                class_="p-6",
            ),
        )
        return HTMLResponse(html)
