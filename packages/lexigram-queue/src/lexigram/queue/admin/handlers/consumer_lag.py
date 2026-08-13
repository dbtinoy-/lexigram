"""Consumer lag widget handler."""

from __future__ import annotations

from lexigram.contracts.admin import (
    QueueStatsProtocol,
    Stat,
    StatContent,
    Tone,
    WidgetParams,
)
from lexigram.contracts.admin.errors import AdminError
from lexigram.result import Ok, Result


class ConsumerLagWidgetHandler:
    """Fetches consumer lag metric.

    Reads ``processing`` from any injected queue that implements the
    ``QueueStatsProtocol`` capability; degrades gracefully otherwise.

    Args:
        queue: Capability object exposing ``get_stats()``, or ``None``.
    """

    def __init__(self, queue: object | None = None) -> None:
        self._queue = queue

    async def get_data(self, params: WidgetParams) -> Result[StatContent, AdminError]:
        """Fetch consumer lag data.

        Args:
            params: Widget parameters.

        Returns:
            Result containing StatContent or AdminError.
        """
        if not isinstance(self._queue, QueueStatsProtocol):
            return Ok(
                StatContent(
                    stats=(
                        Stat(
                            label="Consumer Lag",
                            value="Unavailable",
                            tone=Tone.WARNING,
                        ),
                    )
                )
            )
        stats = self._queue.get_stats() or {}
        processing = int(stats.get("processing", 0))
        return Ok(
            StatContent(
                stats=(
                    Stat(
                        label="Consumer Lag",
                        value=str(processing),
                        tone=Tone.SUCCESS if processing < 100 else Tone.WARNING,
                    ),
                )
            )
        )


__all__ = ["ConsumerLagWidgetHandler"]
