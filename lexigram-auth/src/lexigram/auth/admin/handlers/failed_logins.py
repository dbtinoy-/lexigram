"""Failed logins widget handler."""

from __future__ import annotations

from lexigram.auth.admin.viewmodels import FailedLoginsViewModel
from lexigram.contracts.admin.errors import AdminError
from lexigram.contracts.admin.types import WidgetParams
from lexigram.contracts.ai.session import SessionManagerProtocol
from lexigram.result import Ok, Result


class FailedLoginsWidgetHandler:
    """Handler for the failed logins widget.

    Args:
        session_manager: injected SessionManagerProtocol.
    """

    def __init__(self, session_manager: SessionManagerProtocol) -> None:
        """Initialize handler with session manager.

        Args:
            session_manager: SessionManagerProtocol for login failure tracking.
        """
        self._session_manager = session_manager

    async def get_data(
        self, params: WidgetParams
    ) -> Result[FailedLoginsViewModel, AdminError]:
        """Fetch failed login statistics.

        Infrastructure failures propagate as exceptions.

        Args:
            params: Widget parameters (includes time_window_minutes).

        Returns:
            Result containing FailedLoginsViewModel or AdminError.
        """
        # TODO: Implement failed login tracking
        # For now, return safe defaults (0, 0, False)
        count = 0
        unique_ips = 0
        is_elevated = False

        return Ok(
            FailedLoginsViewModel(
                count=count, unique_ips=unique_ips, is_elevated=is_elevated
            )
        )


__all__ = ["FailedLoginsWidgetHandler"]
