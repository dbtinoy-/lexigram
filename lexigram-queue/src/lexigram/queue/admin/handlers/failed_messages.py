"""Failed messages widget handler."""

from __future__ import annotations

from lexigram.contracts.admin import (
    DlqStatsProtocol,
    Stat,
    StatContent,
    Tone,
    WidgetParams,
)
from lexigram.contracts.admin.errors import AdminError
from lexigram.result import Ok, Result


class FailedMessagesWidgetHandler:
    """Fetches failed messages count.

    Reads ``dead_letter_count`` from any injected store that implements
    the ``DlqStatsProtocol`` capability; degrades gracefully otherwise.

    Args:
        queue: Capability object exposing ``get_stats()``, or ``None``.
    """

    def __init__(self, queue: object | None = None) -> None:
        self._queue = queue

    async def get_data(self, params: WidgetParams) -> Result[StatContent, AdminError]:
        """Fetch failed messages data.

        Args:
            params: Widget parameters.

        Returns:
            Result containing StatContent or AdminError.
        """
        if not isinstance(self._queue, DlqStatsProtocol):
            return Ok(
                StatContent(
                    stats=(
                        Stat(
                            label="Failed messages",
                            value="Unavailable",
                            tone=Tone.WARNING,
                        ),
                    )
                )
            )
        stats = self._queue.get_stats() or {}
        count = int(stats.get("dead_letter_count", 0))
        if count > 0:
            value, tone = str(count), Tone.DANGER
        else:
            value, tone = "✓ No failures", Tone.SUCCESS
        return Ok(
            StatContent(stats=(Stat(label="Failed messages", value=value, tone=tone),))
        )


__all__ = ["FailedMessagesWidgetHandler"]
