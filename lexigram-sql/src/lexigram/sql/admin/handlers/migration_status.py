"""Migration status widget handler."""

from __future__ import annotations

from lexigram.contracts.admin.errors import AdminError
from lexigram.contracts.admin.types import WidgetParams
from lexigram.contracts.data import MigrationManagerProtocol
from lexigram.result import Ok, Result
from lexigram.sql.admin.viewmodels import MigrationStatusViewModel


class MigrationStatusWidgetHandler:
    """Fetches migration status.

    Args:
        migration_manager: injected MigrationManagerProtocol.
    """

    def __init__(self, migration_manager: MigrationManagerProtocol) -> None:
        """Initialize the handler.

        Args:
            migration_manager: Migration manager protocol.
        """
        self._migration_manager = migration_manager

    async def get_data(
        self, params: WidgetParams
    ) -> Result[MigrationStatusViewModel, AdminError]:
        """Fetch migration status.

        Infrastructure failures propagate.

        Args:
            params: Widget parameters.

        Returns:
            Result with MigrationStatusViewModel or AdminError.
        """
        # TODO: Implement actual migration status retrieval
        # For now, return hardcoded mock data
        return Ok(
            MigrationStatusViewModel(
                current_version="20240101_000001",
                total_applied=5,
                pending_count=0,
                is_current=True,
            )
        )


__all__ = ["MigrationStatusWidgetHandler"]
