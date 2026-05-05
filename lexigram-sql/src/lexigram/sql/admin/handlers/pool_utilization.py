"""Pool utilization widget handler."""

from __future__ import annotations

from lexigram.contracts.admin import Stat, StatContent, Tone, WidgetParams
from lexigram.contracts.admin.errors import AdminError
from lexigram.contracts.data import DatabaseProviderProtocol
from lexigram.result import Ok, Result


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

    async def get_data(self, params: WidgetParams) -> Result[StatContent, AdminError]:
        """Fetch pool stats.

        Mirror of the widget template, which renders the metric value
        statically — no tone/threshold logic in the template.

        Infrastructure failures propagate as exceptions.

        Args:
            params: Widget parameters.

        Returns:
            Result with StatContent or AdminError.
        """
        # TODO: Implement actual pool stats retrieval
        # For now, return hardcoded mock data
        pool_size = 20
        active_connections = 8
        utilization_pct = round(40.0, 1)
        return Ok(
            StatContent(
                stats=(
                    Stat(
                        label="Active Connections",
                        value=f"{active_connections}/{pool_size}",
                        tone=Tone.PRIMARY,
                    ),
                    Stat(
                        label="Utilization",
                        value=f"{utilization_pct}%",
                    ),
                )
            )
        )


__all__ = ["PoolUtilizationWidgetHandler"]
