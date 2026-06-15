"""Events throughput widget handler."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.admin import Stat, StatContent, Tone, WidgetParams
from lexigram.contracts.admin.errors import AdminError
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

    async def get_data(self, params: WidgetParams) -> Result[StatContent, AdminError]:
        """Fetch event throughput metrics.

        Returns stub data pending EventBusProtocol stats methods.
        Mirrors the widget template, which applies neutral styling only.
        Infrastructure failures propagate as exceptions.

        Args:
            params: Widget request parameters (contains time_window_minutes).

        Returns:
            Result containing StatContent or AdminError.
        """
        # TODO: Replace with actual EventBus stats when protocol supports it
        events_per_second = 0.0
        total_events = 0
        window_minutes = params.time_window_minutes

        return Ok(
            StatContent(
                stats=(
                    Stat(
                        label="Events/sec",
                        value=f"{events_per_second}/s",
                        tone=Tone.PRIMARY,
                    ),
                    Stat(
                        label=f"Total ({window_minutes}m)",
                        value=str(total_events),
                    ),
                )
            )
        )


__all__ = ["EventsThroughputWidgetHandler"]
