from __future__ import annotations

from typing import Any

from lexigram.contracts.admin import PageContent
from lexigram.contracts.admin.widget_content import Stat, StatContent
from lexigram.contracts.queue.protocols import QueueProtocol
from lexigram.logging import get_logger

logger = get_logger(__name__)


class QueueOverviewPage:
    def __init__(
        self,
        queue: QueueProtocol | None = None,
    ) -> None:
        self._queue = queue

    async def handle(self, request: Any) -> PageContent:
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
            except Exception:  # noqa: S110 — intentional best-effort fallback
                pass

        return PageContent(
            title="Queue",
            body=StatContent(
                stats=(
                    Stat(label="Queue Depth", value=depth, icon="inbox"),
                    Stat(label="Consumer Lag", value=lag, icon="clock"),
                    Stat(label="Failed Messages", value=failed, icon="alert-circle"),
                )
            ),
        )
