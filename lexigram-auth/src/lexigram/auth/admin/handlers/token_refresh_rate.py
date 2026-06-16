"""Token refresh rate widget handler."""

from __future__ import annotations

from lexigram.contracts.admin import Stat, StatContent, WidgetParams
from lexigram.contracts.admin.errors import AdminError
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

    async def get_data(self, params: WidgetParams) -> Result[StatContent, AdminError]:
        """Fetch token refresh rate data.

        Mirrors the widget template: the rate is rendered with one decimal
        and neutral styling, and the total line is shown only when non-zero —
        no tone/threshold ladder exists in the template.

        Infrastructure failures propagate as exceptions.

        Args:
            params: Widget parameters (includes time_window_minutes).

        Returns:
            Result containing StatContent or AdminError.
        """
        # TODO: Implement token refresh metrics tracking
        # For now, return safe defaults (0.0)
        refreshes_per_minute = 0.0
        total_refreshes = 0

        return Ok(
            self._build_content(
                refreshes_per_minute=refreshes_per_minute,
                total_refreshes=total_refreshes,
            )
        )

    def _build_content(
        self, refreshes_per_minute: float, total_refreshes: int
    ) -> StatContent:
        """Build the StatContent mirroring the widget template.

        Args:
            refreshes_per_minute: Token refreshes per minute.
            total_refreshes: Total refresh count.

        Returns:
            StatContent with neutral styling and a conditional total stat.
        """
        stats: list[Stat] = [
            Stat(
                label="Refresh Rate (per minute)",
                value=f"{refreshes_per_minute:.1f}",
            ),
        ]
        if total_refreshes > 0:
            stats.append(Stat(label="Total refreshes", value=str(total_refreshes)))
        return StatContent(stats=tuple(stats))


__all__ = ["TokenRefreshRateWidgetHandler"]
