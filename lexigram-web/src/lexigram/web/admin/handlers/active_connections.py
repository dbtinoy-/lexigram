"""Active connections widget handler for web admin dashboard."""

from __future__ import annotations

from lexigram.contracts.admin import Stat, StatContent, Tone, WidgetParams
from lexigram.contracts.admin.errors import AdminError
from lexigram.result import Ok, Result


class ActiveConnectionsWidgetHandler:
    """Handler for the active_connections widget.

    Fetches current and peak connection counts.
    For now, returns reasonable defaults (TODO: integrate with actual connection tracking).
    """

    async def get_data(self, params: WidgetParams) -> Result[StatContent, AdminError]:
        """Fetch active connections data.

        Args:
            params: Widget request parameters (unused for this widget).

        Returns:
            Result containing StatContent with connection metrics.
        """
        active, peak, max_allowed = 42, 128, 512
        ratio = active / max_allowed
        tone = (
            Tone.DANGER
            if ratio > 0.9
            else Tone.WARNING
            if ratio > 0.7
            else Tone.SUCCESS
        )
        return Ok(
            StatContent(
                stats=(
                    Stat(label="Active", value=str(active), tone=tone),
                    Stat(label="Peak", value=str(peak)),
                    Stat(label="Max", value=str(max_allowed)),
                )
            )
        )


__all__ = ["ActiveConnectionsWidgetHandler"]
