"""Query stats widget handler."""

from __future__ import annotations

from lexigram.contracts.admin import Stat, StatContent, Tone, WidgetParams
from lexigram.contracts.admin.errors import AdminError
from lexigram.contracts.data import DatabaseProviderProtocol
from lexigram.result import Ok, Result


class QueryStatsWidgetHandler:
    """Fetches aggregate query statistics.

    Args:
        db: injected DatabaseProviderProtocol.
    """

    def __init__(self, db: DatabaseProviderProtocol) -> None:
        """Initialize the handler.

        Args:
            db: Database provider protocol.
        """
        self._db = db

    async def get_data(self, params: WidgetParams) -> Result[StatContent, AdminError]:
        """Fetch query stats.

        Mirrors the widget template's four stat rows, including each row's
        static tone class (slow-query count renders as a warning, error count
        as destructive).

        Infrastructure failures propagate.

        Args:
            params: Widget parameters.

        Returns:
            Result with StatContent or AdminError.
        """
        # TODO: Implement actual query stats retrieval
        # For now, return hardcoded mock data
        total_queries = 1250
        avg_duration_ms = 12.5
        slow_queries = 3
        error_count = 0
        return Ok(
            StatContent(
                stats=(
                    Stat(label="Total Queries", value=str(total_queries)),
                    Stat(label="Avg Duration", value=f"{avg_duration_ms}ms"),
                    Stat(
                        label="Slow Queries", value=str(slow_queries), tone=Tone.WARNING
                    ),
                    Stat(label="Errors", value=str(error_count), tone=Tone.DANGER),
                )
            )
        )


__all__ = ["QueryStatsWidgetHandler"]
