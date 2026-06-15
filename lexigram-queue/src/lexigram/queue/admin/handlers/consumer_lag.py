"""Consumer lag widget handler."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.admin import Stat, StatContent, Tone, WidgetParams
from lexigram.contracts.admin.errors import AdminError
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

    async def get_data(self, params: WidgetParams) -> Result[StatContent, AdminError]:
        """Fetch consumer lag data.

        Mirrors the widget template's tone logic: a lag greater than 100
        messages renders as a warning, otherwise it stays neutral.
        Infrastructure failures propagate.

        Args:
            params: Widget parameters.

        Returns:
            Result containing StatContent or AdminError.
        """
        # Stub implementation — returns zero lag
        # In production, would compute lag from queue backend state
        lag_messages = 0
        lag_seconds = 0.0

        return Ok(
            StatContent(
                stats=(
                    Stat(
                        label="Lag (messages)",
                        value=str(lag_messages),
                        tone=Tone.WARNING if lag_messages > 100 else Tone.DEFAULT,
                    ),
                    Stat(label="Lag (seconds)", value=f"~{lag_seconds}s"),
                )
            )
        )


__all__ = ["ConsumerLagWidgetHandler"]
