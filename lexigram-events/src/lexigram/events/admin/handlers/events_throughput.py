"""Events throughput widget handler."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.admin.errors import AdminError
from lexigram.contracts.admin.types import WidgetParams
from lexigram.events.admin.viewmodels import EventsThroughputViewModel
from lexigram.result import Ok, Result

if TYPE_CHECKING:
    from lexigram.contracts.events import EventBusProtocol


class EventsThroughputWidgetHandler:
    """Fetches events throughput data.

    Dependencies:
        event_bus: Injected EventBusProtocol instance.
    """

    def __init__(self, event_bus: EventBusProtocol) -> None:
        self._event_bus = event_bus

    async def get_data(
        self, params: WidgetParams
    ) -> Result[EventsThroughputViewModel, AdminError]:
        """Fetch event throughput metrics.

        Returns stub data pending EventBusProtocol stats methods.
        Infrastructure failures propagate as exceptions.

        Args:
            params: Widget request parameters (contains time_window_minutes).

        Returns:
            Result containing EventsThroughputViewModel or AdminError.
        """
        # TODO: Replace with actual EventBus stats when protocol supports it
        return Ok(
            EventsThroughputViewModel(
                events_per_second=0.0,
                total_events=0,
                window_minutes=params.time_window_minutes,
            )
        )


__all__ = ["EventsThroughputWidgetHandler"]
