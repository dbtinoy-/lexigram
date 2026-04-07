"""Server status widget handler for web admin dashboard."""

from __future__ import annotations

from lexigram.contracts.admin.errors import AdminError
from lexigram.contracts.admin.types import WidgetParams
from lexigram.result import Ok, Result
from lexigram.web.admin.viewmodels import ServerStatusViewModel


class ServerStatusWidgetHandler:
    """Handler for the server_status widget.

    Fetches server status information and uptime.
    For now, returns reasonable defaults (TODO: integrate with actual server stats).
    """

    async def get_data(
        self, params: WidgetParams
    ) -> Result[ServerStatusViewModel, AdminError]:
        """Fetch server status data.

        Args:
            params: Widget request parameters (unused for this widget).

        Returns:
            Result containing ServerStatusViewModel with server status.
        """
        viewmodel = ServerStatusViewModel(
            is_running=True,
            uptime_seconds=3600,  # 1 hour
            server_version="1.0.0",
        )
        return Ok(viewmodel)


__all__ = ["ServerStatusWidgetHandler"]
