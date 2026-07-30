from __future__ import annotations

from typing import Any

from lexigram.contracts.admin import PageContent
from lexigram.contracts.admin.widget_content import (
    EmptyContent,
    TableCell,
    TableContent,
)
from lexigram.contracts.queue.protocols import QueueProtocol
from lexigram.logging import get_logger

logger = get_logger(__name__)


class QueueConsumersPage:
    def __init__(
        self,
        queue: QueueProtocol | None = None,
    ) -> None:
        self._queue = queue

    async def handle(self, request: Any) -> PageContent:
        if self._queue is None:
            return PageContent(
                title="Consumers",
                body=EmptyContent(
                    title="Queue Service Unavailable",
                    message="No queue backend is configured. Consumer data cannot be displayed.",
                    icon="cpu",
                ),
            )

        try:
            health = await self._queue.health_check(timeout=5.0)
            consumers = health.details.get("consumers", []) if health.details else []
        except Exception:
            return PageContent(
                title="Consumers",
                body=EmptyContent(
                    title="Error Loading Consumers",
                    message="Failed to load consumer data. Check the server logs for details.",
                    icon="alert-triangle",
                ),
            )

        if not consumers:
            return PageContent(
                title="Consumers",
                body=EmptyContent(
                    title="No Consumers",
                    message="No consumers are currently registered.",
                    icon="cpu",
                ),
            )

        rows = tuple(
            (
                TableCell(str(c.get("name", "Unknown"))),
                TableCell(str(c.get("topic", ""))),
                TableCell("Active" if c.get("active", False) else "Idle"),
            )
            for c in consumers
        )

        return PageContent(
            title="Consumers",
            body=TableContent(columns=("Name", "Topic", "Status"), rows=rows),
        )
