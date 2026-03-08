from __future__ import annotations

from typing import Any

from starlette.responses import HTMLResponse

from lexigram.contracts.queue.protocols import QueueProtocol
from lexigram.logging import get_logger
from lexigram.ui import Card, Divider, Grid, StatCard, el, render_to_string

logger = get_logger(__name__)


class QueueOverviewPage:
    def __init__(
        self,
        queue: QueueProtocol | None = None,
    ) -> None:
        self._queue = queue

    async def handle(self, request: Any) -> HTMLResponse:
        depth = "N/A"
        lag = "N/A"
        failed = "N/A"
        metrics: dict[str, Any] = {}

        if self._queue is not None:
            try:
                health = await self._queue.health_check(timeout=5.0)
                metrics = health.details or {}
                depth = str(metrics.get("depth", "N/A"))
                lag = str(metrics.get("consumer_lag", "N/A"))
                failed = str(metrics.get("failed_count", "N/A"))
            except Exception:
                pass

        dl_items: list[Any] = []
        for key, label in [
            ("backend", "Backend"),
            ("driver", "Driver"),
            ("depth", "Queue Depth"),
            ("consumer_lag", "Consumer Lag"),
            ("failed_count", "Failed Count"),
            ("pending_jobs", "Pending Jobs"),
            ("processing_jobs", "Processing Jobs"),
            ("completed_jobs", "Completed Jobs"),
        ]:
            value = str(metrics.get(key, "N/A")) if metrics else "N/A"
            dl_items.append(
                el(
                    "dt",
                    label,
                    class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                )
            )
            dl_items.append(
                el("dd", value, class_="text-sm text-[var(--foreground)] pb-3")
            )

        html = render_to_string(
            el(
                "div",
                el("h1", "Queue", class_="text-2xl font-bold text-[var(--foreground)]"),
                el(
                    "p",
                    "Message queue depth, consumer lag, and error monitoring.",
                    class_="text-sm text-[var(--muted-foreground)] mt-1 mb-6",
                ),
                Divider(),
                Grid(
                    StatCard(label="Queue Depth", value=depth, icon="inbox"),
                    StatCard(label="Consumer Lag", value=lag, icon="clock"),
                    StatCard(
                        label="Failed Messages", value=failed, icon="alert-circle"
                    ),
                    cols={"default": 1, "lg": 3},
                    gap=4,
                    class_="mb-6 mt-6",
                ),
                Card(
                    title="Queue Overview",
                    content=render_to_string(
                        el(
                            "dl",
                            *dl_items,
                            class_="divide-y divide-[var(--border)]",
                        )
                    ),
                ),
                class_="p-6",
            ),
        )
        return HTMLResponse(html)
