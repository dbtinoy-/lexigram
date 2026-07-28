"""Average task duration widget handler."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.admin.errors import AdminError
from lexigram.contracts.admin.types import WidgetParams
from lexigram.result import Ok, Result
from lexigram.tasks.admin.viewmodels import AvgDurationViewModel


class AvgDurationWidgetHandler:
    """Fetches average task execution duration statistics.

    Args:
        scheduler_or_metrics: Injected task scheduler or metrics provider (Any).
    """

    def __init__(self, scheduler_or_metrics: Any = None) -> None:
        self._scheduler_or_metrics = scheduler_or_metrics

    async def get_data(
        self, params: WidgetParams
    ) -> Result[AvgDurationViewModel, AdminError]:
        """Fetch average duration statistics.

        Args:
            params: Widget parameters.

        Returns:
            Result containing AvgDurationViewModel or AdminError.
        """
        # TODO: Integrate with metrics collector to fetch real duration stats.
        # For now, return stub data.
        return Ok(
            AvgDurationViewModel(
                avg_ms=0.0,
                p95_ms=0.0,
                window_minutes=params.time_window_minutes,
            )
        )


__all__ = ["AvgDurationWidgetHandler"]
