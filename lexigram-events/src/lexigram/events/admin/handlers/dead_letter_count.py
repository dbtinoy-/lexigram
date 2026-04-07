"""Dead letter count widget handler."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.admin.errors import AdminError
from lexigram.contracts.admin.types import WidgetParams
from lexigram.events.admin.viewmodels import DeadLetterCountViewModel
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

    async def get_data(
        self, params: WidgetParams
    ) -> Result[DeadLetterCountViewModel, AdminError]:
        """Fetch dead letter queue count and age.

        Returns stub data pending EventBusProtocol dead-letter methods.
        Infrastructure failures propagate as exceptions.

        Args:
            params: Widget request parameters.

        Returns:
            Result containing DeadLetterCountViewModel or AdminError.
        """
        # TODO: Replace with actual dead-letter queue stats when protocol supports it
        return Ok(DeadLetterCountViewModel(count=0, oldest_age_minutes=None))


__all__ = ["DeadLetterCountWidgetHandler"]
