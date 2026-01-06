"""Failed messages widget handler."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.admin.errors import AdminError
from lexigram.contracts.admin.types import WidgetParams
from lexigram.queue.admin.viewmodels import FailedMessagesViewModel
from lexigram.result import Ok, Result


class FailedMessagesWidgetHandler:
    """Fetches failed messages count.

    Args:
        queue: Injected QueueProtocol.
    """

    def __init__(
        self, queue: Any
    ) -> None:  # TODO: Replace Any with QueueProtocol when available
        self._queue = queue

    async def get_data(
        self, params: WidgetParams
    ) -> Result[FailedMessagesViewModel, AdminError]:
        """Fetch failed messages data.

        Infrastructure failures propagate.

        Args:
            params: Widget parameters.

        Returns:
            Result containing FailedMessagesViewModel or AdminError.
        """
        # Stub implementation — returns zero failed messages
        # In production, would query DLQ or dead-letter storage
        return Ok(
            FailedMessagesViewModel(
                count=0,
                oldest_age_minutes=None,
            )
        )


__all__ = ["FailedMessagesWidgetHandler"]
