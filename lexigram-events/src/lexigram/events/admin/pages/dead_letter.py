from __future__ import annotations

from typing import Any

from starlette.responses import HTMLResponse

from lexigram.contracts.events import EventBusProtocol
from lexigram.logging import get_logger
from lexigram.ui import Badge, Divider, EmptyState, el, render_to_string

logger = get_logger(__name__)


class EventsDeadLetterPage:
    """Dead-letter queue viewer for /admin/events/dead-letter."""

    def __init__(self, event_bus: EventBusProtocol | None = None) -> None:
        self._event_bus = event_bus

    async def handle(self, request: Any) -> HTMLResponse:
        if self._event_bus is None:
            html = render_to_string(
                EmptyState(
                    title="Event Bus Unavailable",
                    message="No event bus is configured. Dead-letter queue cannot be displayed.",
                    icon="alert-triangle",
                ),
            )
            return HTMLResponse(html)

        entries: list[Any] = []
        try:
            store = getattr(self._event_bus, "dead_letter_store", None)
            if store is not None:
                entries = await store.list_entries(limit=100)
        except Exception as exc:
            logger.warning("events_dead_letter.store_unavailable", error=str(exc))
            html = render_to_string(
                EmptyState(
                    title="Dead-Letter Store Error",
                    message="Failed to retrieve entries from the dead-letter store.",
                    icon="alert-triangle",
                ),
            )
            return HTMLResponse(html)

        if not entries:
            html = render_to_string(
                EmptyState(
                    title="No Dead-Letter Entries",
                    message="No events have been sent to the dead-letter queue.",
                    icon="inbox",
                ),
            )
            return HTMLResponse(html)

        rows = "".join(
            render_to_string(
                el(
                    "tr",
                    el(
                        "td",
                        getattr(e, "event_type", ""),
                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--foreground)]",
                    ),
                    el(
                        "td",
                        getattr(e, "handler_name", ""),
                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--muted-foreground)]",
                    ),
                    el(
                        "td",
                        str(getattr(e, "failed_at", "")),
                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--muted-foreground)]",
                    ),
                    el(
                        "td",
                        Badge(
                            "Replayed" if getattr(e, "replayed", False) else "Pending",
                            variant="success"
                            if getattr(e, "replayed", False)
                            else "warning",
                        ),
                        class_="px-4 py-3 whitespace-nowrap text-sm",
                    ),
                )
            )
            for e in entries
        )

        html = render_to_string(
            el(
                "div",
                el(
                    "h1",
                    "Dead-Letter Queue",
                    class_="text-2xl font-bold text-[var(--foreground)]",
                ),
                el(
                    "p",
                    "Events that failed processing and were routed to the dead-letter queue.",
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
                                    "Event Type",
                                    style="width:25%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                                el(
                                    "th",
                                    "Handler",
                                    style="width:25%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                                el(
                                    "th",
                                    "Failed At",
                                    style="width:25%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                                el(
                                    "th",
                                    "Status",
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
                class_="p-6",
            ),
        )
        return HTMLResponse(html)
