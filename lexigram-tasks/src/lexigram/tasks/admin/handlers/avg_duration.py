"""Average task duration widget handler."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.admin import Stat, StatContent, Tone, WidgetParams
from lexigram.contracts.admin.errors import AdminError
from lexigram.result import Ok, Result


class AvgDurationWidgetHandler:
    """Fetches average task execution duration statistics.

    Args:
        scheduler_or_metrics: Injected task scheduler or metrics provider (Any).
    """

    def __init__(self, scheduler_or_metrics: Any = None) -> None:
        self._scheduler_or_metrics = scheduler_or_metrics

    async def get_data(self, params: WidgetParams) -> Result[StatContent, AdminError]:
        """Fetch average duration statistics.

        Mirrors the widget template's two dl rows, including the P95 row's
        static warning class. The template has no tone/threshold logic.

        Args:
            params: Widget parameters.

        Returns:
            Result containing StatContent or AdminError.
        """
        # TODO: Integrate with metrics collector to fetch real duration stats.
        # For now, return stub data.
        avg_ms = 0.0
        p95_ms = 0.0
        return Ok(
            StatContent(
                stats=(
                    Stat(label="Avg", value=f"{avg_ms}ms"),
                    Stat(label="P95", value=f"{p95_ms}ms", tone=Tone.WARNING),
                )
            )
        )


__all__ = ["AvgDurationWidgetHandler"]
