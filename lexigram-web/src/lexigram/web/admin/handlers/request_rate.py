"""Request rate widget handler for web admin dashboard."""

from __future__ import annotations

from lexigram.contracts.admin.errors import AdminError
from lexigram.contracts.admin.types import WidgetParams
from lexigram.result import Ok, Result
from lexigram.web.admin.viewmodels import RequestRateViewModel


class RequestRateWidgetHandler:
    """Handler for the request_rate widget.

    Fetches current request rate and error metrics.
    For now, returns reasonable defaults (TODO: integrate with actual request tracking).
    """

    async def get_data(
        self, params: WidgetParams
    ) -> Result[RequestRateViewModel, AdminError]:
        """Fetch request rate data.

        Args:
            params: Widget request parameters (unused for this widget).

        Returns:
            Result containing RequestRateViewModel with request metrics.
        """
        viewmodel = RequestRateViewModel(
            requests_per_second=12.5,
            total_requests=45000,
            error_rate_pct=0.5,
        )
        return Ok(viewmodel)


__all__ = ["RequestRateWidgetHandler"]
