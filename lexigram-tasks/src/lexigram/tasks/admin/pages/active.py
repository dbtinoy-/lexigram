"""Management page for /admin/tasks/active."""

from __future__ import annotations

from typing import Any

from starlette.responses import HTMLResponse

from lexigram.logging import get_logger
from lexigram.tasks import WorkerPool
from lexigram.ui import Card, Divider, EmptyState, el, render_to_string

logger = get_logger(__name__)


class TasksActivePage:
    """Management view for /admin/tasks/active."""

    def __init__(self, worker_pool: WorkerPool | None = None) -> None:
        self._worker_pool = worker_pool

    async def handle(self, request: Any) -> HTMLResponse:
        """Handle request and render active tasks page."""
        if self._worker_pool is None:
            html = render_to_string(
                EmptyState(
                    title="Worker Pool Unavailable",
                    message="No worker pool service is configured.",
                    icon="play-circle",
                )
            )
            return HTMLResponse(html)

        try:
            tasks = await self._worker_pool.get_active_tasks()
        except Exception as exc:
            logger.warning("tasks_active.pool_unavailable", error=str(exc))
            html = render_to_string(
                EmptyState(
                    title="Worker Pool Error",
                    message="Failed to retrieve active tasks from the worker pool.",
                    icon="alert-triangle",
                )
            )
            return HTMLResponse(html)

        if not tasks:
            html = render_to_string(
                EmptyState(
                    title="No Active Tasks",
                    message="There are currently no tasks running.",
                    icon="play-circle",
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
                        class_="px-4 py-3 whitespace-nowrap text-xs font-mono text-[var(--foreground)]",
                    ),
                    el(
                        "td",
                        str(t.name),
                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--muted-foreground)]",
                    ),
                    el(
                        "td",
                        str(getattr(t, "started_at", "")),
                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--muted-foreground)]",
                    ),
                    el(
                        "td",
                        str(getattr(t, "duration_ms", "")),
                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--muted-foreground)]",
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
                    "Active Tasks",
                    class_="text-2xl font-bold text-[var(--foreground)]",
                ),
                el(
                    "p",
                    "View currently running background tasks.",
                    class_="text-sm text-[var(--muted-foreground)] mt-1 mb-6",
                ),
                Divider(),
                Card(
                    title="Active Tasks",
                    content=render_to_string(
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
                                            style="width:25%",
                                            class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                        ),
                                        el(
                                            "th",
                                            "Name",
                                            style="width:25%",
                                            class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                        ),
                                        el(
                                            "th",
                                            "Started",
                                            style="width:25%",
                                            class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                        ),
                                        el(
                                            "th",
                                            "Duration",
                                            style="width:25%",
                                            class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
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
                    ),
                ),
                class_="p-6",
            ),
        )
        return HTMLResponse(html)
