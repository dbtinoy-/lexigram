"""Queue depth widget handler."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.admin.errors import AdminError
from lexigram.contracts.admin.types import WidgetParams
from lexigram.queue.admin.viewmodels import QueueDepthViewModel
from lexigram.result import Ok, Result


class QueueDepthWidgetHandler:
    """Fetches queue depth metric.

    Args:
        queue: Injected QueueProtocol.
    """

    def __init__(
        self, queue: Any
    ) -> None:  # TODO: Replace Any with QueueProtocol when available
        self._queue = queue

    async def get_data(
        self, params: WidgetParams
    ) -> Result[QueueDepthViewModel, AdminError]:
        """Fetch queue depth data.

        Infrastructure failures propagate.

        Args:
            params: Widget parameters.

        Returns:
            Result containing QueueDepthViewModel or AdminError.
        """
        # Stub implementation — returns zero depth
        # In production, would query the queue backend for actual depth
        return Ok(
            QueueDepthViewModel(
                depth=0,
                max_depth=None,
                queue_name="default",
            )
        )


__all__ = ["QueueDepthWidgetHandler"]
