"""Migration status widget handler."""

from __future__ import annotations

from lexigram.contracts.admin import HealthCheckPayload, WidgetParams
from lexigram.contracts.admin.errors import AdminError
from lexigram.contracts.core.health import HealthStatus
from lexigram.contracts.data import MigrationManagerProtocol
from lexigram.result import Ok, Result


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
    ) -> Result[HealthCheckPayload, AdminError]:
        """Fetch migration status.

        Mirrors the widget template's ``{% if is_current %}`` logic: an
        up-to-date state renders as a success badge, otherwise a warning
        (``DEGRADED`` → ``Tone.WARNING``).

        Infrastructure failures propagate.

        Args:
            params: Widget parameters.

        Returns:
            Result with HealthCheckPayload or AdminError.
        """
        # TODO: Implement actual migration status retrieval
        # For now, return hardcoded mock data
        current_version = "20240101_000001"
        total_applied = 5
        pending_count = 0
        is_current = True
        return Ok(
            HealthCheckPayload(
                status=(HealthStatus.HEALTHY if is_current else HealthStatus.DEGRADED),
                component="sql.migrations",
                detail=f"Version {current_version}; {total_applied} applied",
            )
        )


__all__ = ["MigrationStatusWidgetHandler"]
