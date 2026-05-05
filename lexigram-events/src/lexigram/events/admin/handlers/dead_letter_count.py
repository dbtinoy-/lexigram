"""Dead letter count widget handler."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.admin import Stat, StatContent, Tone, WidgetParams
from lexigram.contracts.admin.errors import AdminError
from lexigram.result import Ok, Result

if TYPE_CHECKING:
    from lexigram.contracts.events import EventBusProtocol


class DeadLetterCountWidgetHandler:
    """Fetches dead letter queue count and statistics.

    Dependencies:
        event_bus: Injected EventBusProtocol instance.
    """

    def __init__(self, event_bus: EventBusProtocol) -> None:
        self._event_bus = event_bus

    async def get_data(self, params: WidgetParams) -> Result[StatContent, AdminError]:
        """Fetch dead letter queue count and age.

        Returns stub data pending EventBusProtocol dead-letter methods.
        Mirrors the widget template: a non-zero count is a danger signal,
        a clear queue renders as success.
        Infrastructure failures propagate as exceptions.

        Args:
            params: Widget request parameters.

        Returns:
            Result containing StatContent or AdminError.
        """
        # TODO: Replace with actual dead-letter queue stats when protocol supports it
        count = 0
        oldest_age_minutes: int | None = None

        stats: list[Stat] = [
            Stat(
                label="Dead Letters",
                value=str(count) if count > 0 else "✓ Queue clear",
                tone=Tone.DANGER if count > 0 else Tone.SUCCESS,
            )
        ]
        if oldest_age_minutes is not None:
            stats.append(Stat(label="Oldest", value=f"{oldest_age_minutes}m ago"))

        return Ok(StatContent(stats=tuple(stats)))


__all__ = ["DeadLetterCountWidgetHandler"]
