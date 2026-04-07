"""Management page for /admin/tasks/failed."""

from __future__ import annotations

from typing import Any

from starlette.responses import HTMLResponse

from lexigram.logging import get_logger
from lexigram.tasks import ResultStore
from lexigram.ui import Badge, Divider, EmptyState, el, render_to_string

logger = get_logger(__name__)


class TasksFailedPage:
    """Management view for /admin/tasks/failed."""

    def __init__(self, result_store: ResultStore | None = None) -> None:
        self._result_store = result_store

    async def handle(self, request: Any) -> HTMLResponse:
        """Handle request and render failed tasks page."""
        if self._result_store is None:
            html = render_to_string(
                EmptyState(
                    title="Result Store Unavailable",
                    message="No result store service is configured.",
                    icon="x-circle",
                )
            )
            return HTMLResponse(html)

        try:
            tasks = await self._result_store.get_failed()
        except Exception as exc:
            logger.warning("tasks_failed.store_unavailable", error=str(exc))
            html = render_to_string(
                EmptyState(
                    title="Result Store Error",
                    message="Failed to retrieve failed tasks from the result store.",
                    icon="alert-triangle",
                )
            )
            return HTMLResponse(html)

        if not tasks:
            html = render_to_string(
                EmptyState(
                    title="No Failed Tasks",
                    message="There are no failed tasks to display.",
                    icon="x-circle",
                )
            )
            return HTMLResponse(html)

        rows = "".join(
            render_to_string(
                el(
                    "tr",
                    el(
                        "td",
                        str(t.id),
                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--foreground)]",
                    ),
                    el(
                        "td",
                        str(t.name),
                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--muted-foreground)]",
                    ),
                    el(
                        "td",
                        str(getattr(t, "failed_at", "")),
                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--muted-foreground)]",
                    ),
                    el(
                        "td",
                        Badge("Failed", variant="danger"),
                        class_="px-4 py-3 whitespace-nowrap text-sm",
                    ),
                    el(
                        "td",
                        str(getattr(t, "error", "")),
                        class_="px-4 py-3 whitespace-nowrap text-sm text-red-500 max-w-xs truncate text-right",
                    ),
                )
            )
            for t in tasks
        )

        html = render_to_string(
            el(
                "div",
                el(
                    "h1",
                    "Failed Tasks",
                    class_="text-2xl font-bold text-[var(--foreground)]",
                ),
                el(
                    "p",
                    "Background tasks that terminated with errors.",
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
                                    "ID",
                                    style="width:15%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                                el(
                                    "th",
                                    "Name",
                                    style="width:20%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                                el(
                                    "th",
                                    "Failed At",
                                    style="width:15%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                                el(
                                    "th",
                                    "Status",
                                    style="width:12%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                                el(
                                    "th",
                                    "Error",
                                    style="width:38%",
                                    class_="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                            ),
                        ),
                        el(
                            "tbody",
                            rows,
                            class_="divide-y divide-[var(--border)]",
                        ),
                        class_="min-w-full table-fixed divide-y divide-[var(--border)]",
                    ),
                    class_="overflow-x-auto rounded-xl border border-[var(--border)] bg-[var(--card)]",
                ),
                class_="p-6",
            ),
        )
        return HTMLResponse(html)
