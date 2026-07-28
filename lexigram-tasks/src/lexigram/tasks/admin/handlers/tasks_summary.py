"""Tasks summary widget handler."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.admin.errors import AdminError
from lexigram.contracts.admin.types import WidgetParams
from lexigram.result import Ok, Result
from lexigram.tasks.admin.viewmodels import TasksSummaryViewModel


class TasksSummaryWidgetHandler:
    """Fetches task queue summary statistics.

    Args:
        queue_provider: Injected task queue (Any until we have a dedicated protocol).
    """

    def __init__(self, queue_provider: Any = None) -> None:
        self._queue_provider = queue_provider

    async def get_data(
        self, params: WidgetParams
    ) -> Result[TasksSummaryViewModel, AdminError]:
        """Fetch task summary statistics.

        Args:
            params: Widget parameters.

        Returns:
            Result containing TasksSummaryViewModel or AdminError.
        """
        # TODO: Integrate with actual task queue to fetch real stats.
        # For now, return stub data.
        return Ok(
            TasksSummaryViewModel(
                pending=0,
                running=0,
                completed=0,
                failed=0,
            )
        )


__all__ = ["TasksSummaryWidgetHandler"]
