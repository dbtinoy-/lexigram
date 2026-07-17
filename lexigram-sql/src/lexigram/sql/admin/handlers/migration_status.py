"""Migration status widget handler."""

from __future__ import annotations

from lexigram.contracts.admin import Stat, StatContent, Tone, WidgetParams
from lexigram.contracts.admin.errors import AdminError
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

    async def get_data(self, params: WidgetParams) -> Result[StatContent, AdminError]:
        """Fetch migration status.

        Reports applied and pending migration counts; a fully migrated
        state renders as success, otherwise a warning.

        Args:
            params: Widget parameters.

        Returns:
            Result with StatContent or AdminError.
        """
        applied = await self._migration_manager.get_applied_migrations()
        pending = await self._migration_manager.get_pending_migrations()
        return Ok(
            StatContent(
                stats=(
                    Stat(label="Applied", value=f"{len(applied)} applied"),
                    Stat(
                        label="Pending",
                        value=f"{len(pending)} pending",
                        tone=Tone.SUCCESS if not pending else Tone.WARNING,
                    ),
                )
            )
        )


__all__ = ["MigrationStatusWidgetHandler"]
