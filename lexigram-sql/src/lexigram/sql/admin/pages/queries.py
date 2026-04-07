from __future__ import annotations

from typing import Any

from starlette.responses import HTMLResponse

from lexigram.contracts.data.sql.query_log import QueryLoggerProtocol
from lexigram.logging import get_logger
from lexigram.ui import Divider, EmptyState, el, render_to_string

logger = get_logger(__name__)


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
            entries = await self._query_logger.get_recent_queries(limit=50)
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
            for m in entries
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
                class_="p-6",
            ),
        )
        return HTMLResponse(html)
