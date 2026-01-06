"""Active connections widget handler for web admin dashboard."""

from __future__ import annotations

from lexigram.contracts.admin.errors import AdminError
from lexigram.contracts.admin.types import WidgetParams
from lexigram.result import Ok, Result
from lexigram.web.admin.viewmodels import ActiveConnectionsViewModel


class ActiveConnectionsWidgetHandler:
    """Handler for the active_connections widget.

    Fetches current and peak connection counts.
    For now, returns reasonable defaults (TODO: integrate with actual connection tracking).
    """

    async def get_data(
        self, params: WidgetParams
    ) -> Result[ActiveConnectionsViewModel, AdminError]:
        """Fetch active connections data.

        Args:
            params: Widget request parameters (unused for this widget).

        Returns:
            Result containing ActiveConnectionsViewModel with connection metrics.
        """
        viewmodel = ActiveConnectionsViewModel(
            active=42,
            peak=128,
            max_allowed=512,
        )
        return Ok(viewmodel)


__all__ = ["ActiveConnectionsWidgetHandler"]
