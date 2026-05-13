from __future__ import annotations

from typing import Any

from starlette.responses import HTMLResponse

from lexigram.contracts.queue.protocols import QueueProtocol
from lexigram.logging import get_logger
from lexigram.ui import Divider, EmptyState, el, render_to_string

logger = get_logger(__name__)


class QueueJobsPage:
    def __init__(
        self,
        queue: QueueProtocol | None = None,
    ) -> None:
        self._queue = queue

    async def handle(self, request: Any) -> HTMLResponse:
        if self._queue is None:
            html = render_to_string(
                EmptyState(
                    title="Queue Service Unavailable",
                    message="No queue backend is configured. Jobs cannot be displayed.",
                    icon="briefcase",
                ),
            )
            return HTMLResponse(html)

        try:
            health = await self._queue.health_check(timeout=5.0)
            pending = health.details.get("pending_jobs", 0) if health.details else 0
            processing = (
                health.details.get("processing_jobs", 0) if health.details else 0
            )
            completed = health.details.get("completed_jobs", 0) if health.details else 0
        except Exception:
            html = render_to_string(
                EmptyState(
                    title="Error Loading Jobs",
                    message="Failed to load job data. Check the server logs for details.",
                    icon="alert-triangle",
                ),
            )
            return HTMLResponse(html)

        rows = "".join(
            render_to_string(
                el(
                    "tr",
                    el(
                        "td",
                        label,
                        class_="px-4 py-3 whitespace-nowrap text-sm font-medium text-[var(--foreground)]",
                    ),
                    el(
                        "td",
                        el("span", str(count)),
                        class_="px-4 py-3 whitespace-nowrap text-sm",
                    ),
                )
            )
            for label, count in [
                ("Pending", pending),
                ("Processing", processing),
                ("Completed", completed),
            ]
        )

        html = render_to_string(
            el(
                "div",
                el(
                    "h1",
                    "Queue Jobs",
                    class_="text-2xl font-bold text-[var(--foreground)]",
                ),
                el(
                    "p",
                    "Browse pending, processing, and completed queue jobs.",
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
                                    "Status",
                                    style="width:40%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                                el(
                                    "th",
                                    "Count",
                                    style="width:60%",
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
