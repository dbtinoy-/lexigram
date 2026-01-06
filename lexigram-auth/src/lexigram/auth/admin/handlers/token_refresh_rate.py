"""Token refresh rate widget handler."""

from __future__ import annotations

from lexigram.auth.admin.viewmodels import TokenRefreshRateViewModel
from lexigram.contracts.admin.errors import AdminError
from lexigram.contracts.admin.types import WidgetParams
from lexigram.contracts.ai.session import SessionManagerProtocol
from lexigram.result import Ok, Result


class TokenRefreshRateWidgetHandler:
    """Handler for the token refresh rate widget.

    Args:
        session_manager: injected SessionManagerProtocol.
    """

    def __init__(self, session_manager: SessionManagerProtocol) -> None:
        """Initialize handler with session manager.

        Args:
            session_manager: SessionManagerProtocol for token metrics.
        """
        self._session_manager = session_manager

    async def get_data(
        self, params: WidgetParams
    ) -> Result[TokenRefreshRateViewModel, AdminError]:
        """Fetch token refresh rate data.

        Infrastructure failures propagate as exceptions.

        Args:
            params: Widget parameters (includes time_window_minutes).

        Returns:
            Result containing TokenRefreshRateViewModel or AdminError.
        """
        # TODO: Implement token refresh metrics tracking
        # For now, return safe defaults (0.0, 0)
        refreshes_per_minute = 0.0
        total_refreshes = 0

        return Ok(
            TokenRefreshRateViewModel(
                refreshes_per_minute=refreshes_per_minute,
                total_refreshes=total_refreshes,
            )
        )


__all__ = ["TokenRefreshRateWidgetHandler"]
