"""Queue depth widget handler."""

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


class QueueDepthWidgetHandler:
    """Fetches queue depth metric.

    Reads ``pending`` from any injected queue that implements the
    ``QueueStatsProtocol`` capability; degrades gracefully otherwise.

    Args:
        queue: Capability object exposing ``get_stats()``, or ``None``.
    """

    def __init__(self, queue: object | None = None) -> None:
        self._queue = queue

    async def get_data(self, params: WidgetParams) -> Result[StatContent, AdminError]:
        """Fetch queue depth data.

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
                            label="Queue Depth",
                            value="Unavailable",
                            tone=Tone.WARNING,
                        ),
                    )
                )
            )
        stats = self._queue.get_stats() or {}
        pending = int(stats.get("pending", 0))
        return Ok(
            StatContent(
                stats=(
                    Stat(
                        label="Queue Depth",
                        value=str(pending),
                        tone=Tone.SUCCESS if pending < 100 else Tone.WARNING,
                    ),
                )
            )
        )


__all__ = ["QueueDepthWidgetHandler"]
