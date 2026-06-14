"""Request rate widget handler for web admin dashboard."""

from __future__ import annotations

from lexigram.contracts.admin import Stat, StatContent, Tone, WidgetParams
from lexigram.contracts.admin.errors import AdminError
from lexigram.result import Ok, Result


class RequestRateWidgetHandler:
    """Handler for the request_rate widget.

    Fetches current request rate and error metrics.
    For now, returns reasonable defaults (TODO: integrate with actual request tracking).
    """

    async def get_data(self, params: WidgetParams) -> Result[StatContent, AdminError]:
        """Fetch request rate data.

        Args:
            params: Widget request parameters (unused for this widget).

        Returns:
            Result containing StatContent with request metrics.
        """
        rps, total, error_pct = 12.5, 45000, 0.5
        tone = (
            Tone.DANGER
            if error_pct > 5
            else Tone.WARNING
            if error_pct > 1
            else Tone.SUCCESS
        )
        return Ok(
            StatContent(
                stats=(
                    Stat(label="Requests/sec", value=f"{rps:.1f}"),
                    Stat(label="Total", value=str(total)),
                    Stat(label="Error rate", value=f"{error_pct:.1f}%", tone=tone),
                )
            )
        )


__all__ = ["RequestRateWidgetHandler"]
