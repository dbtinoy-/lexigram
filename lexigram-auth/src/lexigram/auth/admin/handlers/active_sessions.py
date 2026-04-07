"""Active sessions widget handler."""

from __future__ import annotations

from lexigram.auth.admin.viewmodels import ActiveSessionsViewModel
from lexigram.contracts.admin.errors import AdminError
from lexigram.contracts.admin.types import WidgetParams
from lexigram.contracts.ai.session import SessionManagerProtocol
from lexigram.result import Ok, Result


class ActiveSessionsWidgetHandler:
    """Handler for the active sessions widget.

    Args:
        session_manager: injected SessionManagerProtocol.
    """

    def __init__(self, session_manager: SessionManagerProtocol) -> None:
        """Initialize handler with session manager.

        Args:
            session_manager: SessionManagerProtocol to retrieve active sessions.
        """
        self._session_manager = session_manager

    async def get_data(
        self, params: WidgetParams
    ) -> Result[ActiveSessionsViewModel, AdminError]:
        """Fetch active sessions data.

        Infrastructure failures propagate as exceptions.

        Args:
            params: Widget parameters (unused for this widget).

        Returns:
            Result containing ActiveSessionsViewModel or AdminError.
        """
        # TODO: Implement actual session statistics retrieval
        # For now, return safe defaults (0, 0)
        count = 0
        peak_today = 0

        return Ok(ActiveSessionsViewModel(count=count, peak_today=peak_today))


__all__ = ["ActiveSessionsWidgetHandler"]
