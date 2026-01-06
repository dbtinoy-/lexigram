from __future__ import annotations

from typing import Any

from starlette.responses import HTMLResponse

from lexigram.contracts.events import EventBusProtocol
from lexigram.logging import get_logger
from lexigram.ui import Card, Divider, Grid, StatCard, el, render_to_string

logger = get_logger(__name__)


class EventsOverviewPage:
    """Dashboard overview for /admin/events."""

    def __init__(self, event_bus: EventBusProtocol | None = None) -> None:
        self._event_bus = event_bus

    async def handle(self, request: Any) -> HTMLResponse:
        subscriber_count: str | int = "N/A"
        throughput: str | int = "N/A"
        dead_letter_count: str | int = "N/A"
        max_concurrent: str | int = "N/A"
        enable_dead_letter: str | bool = "N/A"
        error_count: str | int = "N/A"
        in_flight: str | int = "N/A"

        if self._event_bus is not None:
            config = getattr(self._event_bus, "_config", None)
            if config is not None:
                max_concurrent = getattr(config, "max_concurrent_handlers", "N/A")
                enable_dead_letter = getattr(config, "enable_dead_letter", "N/A")

            try:
                subscribers = getattr(self._event_bus, "_subscribers", {})
                subscriber_count = len(subscribers)
            except Exception:
                subscriber_count = "N/A"

            try:
                dispatch_errors = getattr(self._event_bus, "_dispatch_errors", None)
                error_count = len(dispatch_errors) if dispatch_errors is not None else 0
            except Exception:
                error_count = "N/A"

            try:
                in_flight = getattr(self._event_bus, "_in_flight", 0)
            except Exception:
                in_flight = "N/A"

            try:
                dl_store = getattr(self._event_bus, "dead_letter_store", None)
                if dl_store is not None:
                    get_count = getattr(dl_store, "get_count", None)
                    if get_count is not None:
                        dead_letter_count = await get_count()
            except Exception:
                dead_letter_count = "N/A"

        html = render_to_string(
            el(
                "div",
                el(
                    "h1", "Events", class_="text-2xl font-bold text-[var(--foreground)]"
                ),
                el(
                    "p",
                    "Event bus subscribers, throughput, and dead-letter monitoring.",
                    class_="text-sm text-[var(--muted-foreground)] mt-1 mb-6",
                ),
                Divider(),
                Grid(
                    StatCard(
                        label="Subscribers",
                        value=str(subscriber_count),
                        icon="users",
                    ),
                    StatCard(
                        label="In-Flight",
                        value=str(in_flight),
                        icon="activity",
                    ),
                    StatCard(
                        label="Dead-Letter Count",
                        value=str(dead_letter_count),
                        icon="alert-triangle",
                    ),
                    StatCard(
                        label="Errors",
                        value=str(error_count),
                        icon="x-circle",
                    ),
                    cols={"default": 1, "lg": 4},
                    gap=4,
                    class_="mb-6 mt-6",
                ),
                Card(
                    title="Event Bus Details",
                    content=render_to_string(
                        el(
                            "dl",
                            el(
                                "dt",
                                "Status",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                "Connected"
                                if self._event_bus is not None
                                else "Unavailable",
                                class_="text-sm text-[var(--foreground)] pb-3",
                            ),
                            el(
                                "dt",
                                "Subscriber Count",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                str(subscriber_count),
                                class_="text-sm text-[var(--foreground)] pb-3",
                            ),
                            el(
                                "dt",
                                "In-Flight Events",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                str(in_flight),
                                class_="text-sm text-[var(--foreground)] pb-3",
                            ),
                            el(
                                "dt",
                                "Dead-Letter Count",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                str(dead_letter_count),
                                class_="text-sm text-[var(--foreground)] pb-3",
                            ),
                            el(
                                "dt",
                                "Max Concurrent Handlers",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                str(max_concurrent),
                                class_="text-sm text-[var(--foreground)] pb-3",
                            ),
                            el(
                                "dt",
                                "Dead Letter Enabled",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                str(enable_dead_letter),
                                class_="text-sm text-[var(--foreground)] pb-3",
                            ),
                            el(
                                "dt",
                                "Errors",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                str(error_count),
                                class_="text-sm text-[var(--foreground)] pb-3",
                            ),
                            class_="divide-y divide-[var(--border)]",
                        ),
                    ),
                ),
                class_="p-6",
            ),
        )
        return HTMLResponse(html)
