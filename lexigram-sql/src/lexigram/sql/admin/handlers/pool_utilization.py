"""Pool utilization widget handler."""

from __future__ import annotations

from lexigram.contracts.admin.errors import AdminError
from lexigram.contracts.admin.types import WidgetParams
from lexigram.contracts.data import DatabaseProviderProtocol
from lexigram.result import Ok, Result
from lexigram.sql.admin.viewmodels import PoolUtilizationViewModel


class PoolUtilizationWidgetHandler:
    """Fetches database pool utilization data.

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
    ) -> Result[PoolUtilizationViewModel, AdminError]:
        """Fetch pool stats.

        Infrastructure failures propagate as exceptions.

        Args:
            params: Widget parameters.

        Returns:
            Result with PoolUtilizationViewModel or AdminError.
        """
        # TODO: Implement actual pool stats retrieval
        # For now, return hardcoded mock data
        utilization = 40.0
        return Ok(
            PoolUtilizationViewModel(
                pool_size=20,
                active_connections=8,
                idle_connections=12,
                utilization_pct=round(utilization, 1),
            )
        )


__all__ = ["PoolUtilizationWidgetHandler"]
