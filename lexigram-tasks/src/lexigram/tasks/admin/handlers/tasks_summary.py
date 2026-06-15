"""Tasks summary widget handler."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.admin import Stat, StatContent, Tone, WidgetParams
from lexigram.contracts.admin.errors import AdminError
from lexigram.result import Ok, Result


class TasksSummaryWidgetHandler:
    """Fetches task queue summary statistics.

    Args:
        queue_provider: Injected task queue (Any until we have a dedicated protocol).
    """

    def __init__(self, queue_provider: Any = None) -> None:
        self._queue_provider = queue_provider

    async def get_data(self, params: WidgetParams) -> Result[StatContent, AdminError]:
        """Fetch task summary statistics.

        Mirrors the widget template's four static cells, including each
        cell's static tone class (running is informational, completed is
        success, failed is destructive). The template has no tone/threshold
        logic.

        Args:
            params: Widget parameters.

        Returns:
            Result containing StatContent or AdminError.
        """
        # TODO: Integrate with actual task queue to fetch real stats.
        # For now, return stub data.
        pending = 0
        running = 0
        completed = 0
        failed = 0
        return Ok(
            StatContent(
                stats=(
                    Stat(label="Pending", value=str(pending)),
                    Stat(label="Running", value=str(running), tone=Tone.INFO),
                    Stat(label="Completed", value=str(completed), tone=Tone.SUCCESS),
                    Stat(label="Failed", value=str(failed), tone=Tone.DANGER),
                )
            )
        )


__all__ = ["TasksSummaryWidgetHandler"]
