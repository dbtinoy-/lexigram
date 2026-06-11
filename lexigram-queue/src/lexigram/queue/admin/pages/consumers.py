from __future__ import annotations

from typing import Any

from starlette.responses import HTMLResponse

from lexigram.contracts.queue.protocols import QueueProtocol
from lexigram.logging import get_logger
from lexigram.ui import Badge, Divider, EmptyState, el, raw, render_to_string

logger = get_logger(__name__)


class QueueConsumersPage:
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
                    message="No queue backend is configured. Consumer data cannot be displayed.",
                    icon="cpu",
                ),
            )
            return HTMLResponse(html)

        try:
            health = await self._queue.health_check(timeout=5.0)
            consumers = health.details.get("consumers", []) if health.details else []
        except Exception:
            html = render_to_string(
                EmptyState(
                    title="Error Loading Consumers",
                    message="Failed to load consumer data. Check the server logs for details.",
                    icon="alert-triangle",
                ),
            )
            return HTMLResponse(html)

        if not consumers:
            html = render_to_string(
                EmptyState(
                    title="No Consumers",
                    message="No consumers are currently registered.",
                    icon="cpu",
                ),
            )
            return HTMLResponse(html)

        rows = "".join(
            render_to_string(
                el(
                    "tr",
                    el(
                        "td",
                        c.get("name", "Unknown"),
                        class_="px-4 py-3 whitespace-nowrap text-sm font-medium text-[var(--foreground)]",
                    ),
                    el(
                        "td",
                        c.get("topic", ""),
                        class_="px-4 py-3 whitespace-nowrap text-sm",
                    ),
                    el(
                        "td",
                        Badge(
                            "Active" if c.get("active", False) else "Idle",
                            variant="success" if c.get("active", False) else "warning",
                        ),
                        class_="px-4 py-3 whitespace-nowrap text-sm",
                    ),
                )
            )
            for c in consumers
        )

        html = render_to_string(
            el(
                "div",
                el(
                    "h1",
                    "Consumers",
                    class_="text-2xl font-bold text-[var(--foreground)]",
                ),
                el(
                    "p",
                    "Active message queue consumers and their topics.",
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
                                    "Name",
                                    style="width:30%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                                el(
                                    "th",
                                    "Topic",
                                    style="width:40%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                                el(
                                    "th",
                                    "Status",
                                    style="width:30%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                            ),
                        ),
                        el("tbody", raw(rows), class_="divide-y divide-[var(--border)]"),
                        class_="min-w-full table-fixed divide-y divide-[var(--border)]",
                    ),
                    class_="overflow-x-auto rounded-xl border border-[var(--border)] bg-[var(--card)]",
                ),
                class_="p-6",
            ),
        )
        return HTMLResponse(html)
