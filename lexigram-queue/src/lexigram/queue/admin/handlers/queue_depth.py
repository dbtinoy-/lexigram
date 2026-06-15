"""Queue depth widget handler."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.admin import Stat, StatContent, Tone, WidgetParams
from lexigram.contracts.admin.errors import AdminError
from lexigram.result import Ok, Result


class QueueDepthWidgetHandler:
    """Fetches queue depth metric.

    Args:
        queue: Injected QueueProtocol.
    """

    def __init__(
        self, queue: Any
    ) -> None:  # TODO: Replace Any with QueueProtocol when available
        self._queue = queue

    async def get_data(self, params: WidgetParams) -> Result[StatContent, AdminError]:
        """Fetch queue depth data.

        Mirrors the widget template, which renders the depth value with
        neutral styling and shows a conditional max-depth readout.
        Infrastructure failures propagate.

        Args:
            params: Widget parameters.

        Returns:
            Result containing StatContent or AdminError.
        """
        # Stub implementation — returns zero depth
        # In production, would query the queue backend for actual depth
        depth = 0
        max_depth: int | None = None
        queue_name = "default"

        stats: list[Stat] = [
            Stat(label="Queue", value=queue_name),
            Stat(label="Depth", value=str(depth), tone=Tone.PRIMARY),
        ]
        if max_depth is not None:
            stats.append(Stat(label="Max", value=str(max_depth)))

        return Ok(StatContent(stats=tuple(stats)))


__all__ = ["QueueDepthWidgetHandler"]
