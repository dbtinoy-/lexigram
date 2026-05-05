"""Failed messages widget handler."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.admin import Stat, StatContent, Tone, WidgetParams
from lexigram.contracts.admin.errors import AdminError
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

    async def get_data(self, params: WidgetParams) -> Result[StatContent, AdminError]:
        """Fetch failed messages data.

        Mirrors the widget template, which shows a count in danger styling
        when non-zero and a success readout when the queue is clear.
        Infrastructure failures propagate.

        Args:
            params: Widget parameters.

        Returns:
            Result containing StatContent or AdminError.
        """
        # Stub implementation — returns zero failed messages
        # In production, would query DLQ or dead-letter storage
        count = 0
        oldest_age_minutes: int | None = None

        stats: list[Stat] = []
        if count > 0:
            stats.append(
                Stat(label="Failed messages", value=str(count), tone=Tone.DANGER)
            )
            if oldest_age_minutes is not None:
                stats.append(Stat(label="Oldest", value=f"{oldest_age_minutes}m ago"))
        else:
            stats.append(
                Stat(label="Failed messages", value="✓ No failures", tone=Tone.SUCCESS)
            )

        return Ok(StatContent(stats=tuple(stats)))


__all__ = ["FailedMessagesWidgetHandler"]
