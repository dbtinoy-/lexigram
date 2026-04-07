from __future__ import annotations

from typing import Any

from starlette.responses import HTMLResponse

from lexigram.contracts.events import EventStoreProtocol
from lexigram.logging import get_logger
from lexigram.ui import Divider, EmptyState, el, render_to_string

logger = get_logger(__name__)


class EventsHistoryPage:
    """Event history for /admin/events/history."""

    def __init__(self, store: EventStoreProtocol | None = None) -> None:
        self._store = store

    async def handle(self, request: Any) -> HTMLResponse:
        if self._store is None:
            html = render_to_string(
                EmptyState(
                    title="Event Store Unavailable",
                    message="No event store is configured. History cannot be displayed.",
                    icon="clock",
                ),
            )
            return HTMLResponse(html)

        events: list[Any] = []
        try:
            events = await self._store.read_all(position=0, count=50)
        except Exception as exc:
            logger.warning("events_history.store_unavailable", error=str(exc))
            html = render_to_string(
                EmptyState(
                    title="Event Store Error",
                    message="Failed to retrieve events from the event store.",
                    icon="alert-triangle",
                ),
            )
            return HTMLResponse(html)

        if not events:
            html = render_to_string(
                EmptyState(
                    title="No Events",
                    message="No events have been recorded yet.",
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
                        str(getattr(e, "event_id", "")),
                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--foreground)]",
                    ),
                    el(
                        "td",
                        type(e).__name__,
                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--foreground)]",
                    ),
                    el(
                        "td",
                        str(getattr(e, "occurred_at", "")),
                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--muted-foreground)]",
                    ),
                )
            )
            for e in events
        )

        html = render_to_string(
            el(
                "div",
                el(
                    "h1",
                    "Event History",
                    class_="text-2xl font-bold text-[var(--foreground)]",
                ),
                el(
                    "p",
                    "Recent events published through the event bus.",
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
                                    style="width:30%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                                el(
                                    "th",
                                    "Type",
                                    style="width:35%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                                el(
                                    "th",
                                    "Occurred At",
                                    style="width:35%",
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
