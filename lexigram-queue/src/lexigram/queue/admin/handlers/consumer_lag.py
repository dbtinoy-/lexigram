"""Consumer lag widget handler."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.admin.errors import AdminError
from lexigram.contracts.admin.types import WidgetParams
from lexigram.queue.admin.viewmodels import ConsumerLagViewModel
from lexigram.result import Ok, Result


class ConsumerLagWidgetHandler:
    """Fetches consumer lag metric.

    Args:
        queue: Injected QueueProtocol.
    """

    def __init__(
        self, queue: Any
    ) -> None:  # TODO: Replace Any with QueueProtocol when available
        self._queue = queue

    async def get_data(
        self, params: WidgetParams
    ) -> Result[ConsumerLagViewModel, AdminError]:
        """Fetch consumer lag data.

        Infrastructure failures propagate.

        Args:
            params: Widget parameters.

        Returns:
            Result containing ConsumerLagViewModel or AdminError.
        """
        # Stub implementation — returns zero lag
        # In production, would compute lag from queue backend state
        return Ok(
            ConsumerLagViewModel(
                lag_messages=0,
                lag_seconds=0.0,
            )
        )


__all__ = ["ConsumerLagWidgetHandler"]
