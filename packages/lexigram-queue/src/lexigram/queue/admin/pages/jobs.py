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


class QueueJobsPage:
    def __init__(
        self,
        queue: QueueProtocol | None = None,
    ) -> None:
        self._queue = queue

    async def handle(self, request: Any) -> PageContent:
        if self._queue is None:
            return PageContent(
                title="Queue Jobs",
                body=EmptyContent(
                    title="Queue Service Unavailable",
                    message="No queue backend is configured. Jobs cannot be displayed.",
                    icon="briefcase",
                ),
            )

        try:
            health = await self._queue.health_check(timeout=5.0)
            pending = health.details.get("pending_jobs", 0) if health.details else 0
            processing = (
                health.details.get("processing_jobs", 0) if health.details else 0
            )
            completed = health.details.get("completed_jobs", 0) if health.details else 0
        except Exception:
            return PageContent(
                title="Queue Jobs",
                body=EmptyContent(
                    title="Error Loading Jobs",
                    message="Failed to load job data. Check the server logs for details.",
                    icon="alert-triangle",
                ),
            )

        rows = tuple(
            tuple(TableCell(str(c)) for c in row)
            for row in [
                ("Pending", pending),
                ("Processing", processing),
                ("Completed", completed),
            ]
        )

        return PageContent(
            title="Queue Jobs",
            body=TableContent(columns=("Status", "Count"), rows=rows),
        )
