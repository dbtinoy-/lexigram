"""Query stats widget handler."""

from __future__ import annotations

from lexigram.contracts.admin.errors import AdminError
from lexigram.contracts.admin.types import WidgetParams
from lexigram.contracts.data import DatabaseProviderProtocol
from lexigram.result import Ok, Result
from lexigram.sql.admin.viewmodels import QueryStatsViewModel


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

    async def get_data(
        self, params: WidgetParams
    ) -> Result[QueryStatsViewModel, AdminError]:
        """Fetch query stats.

        Infrastructure failures propagate.

        Args:
            params: Widget parameters.

        Returns:
            Result with QueryStatsViewModel or AdminError.
        """
        # TODO: Implement actual query stats retrieval
        # For now, return hardcoded mock data
        return Ok(
            QueryStatsViewModel(
                total_queries=1250,
                avg_duration_ms=12.5,
                slow_queries=3,
                error_count=0,
            )
        )


__all__ = ["QueryStatsWidgetHandler"]
