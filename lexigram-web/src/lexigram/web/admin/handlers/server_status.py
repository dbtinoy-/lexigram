"""Server status widget handler for web admin dashboard."""

from __future__ import annotations

from lexigram.contracts.admin import HealthCheckPayload, WidgetParams
from lexigram.contracts.admin.errors import AdminError
from lexigram.contracts.core.health import HealthStatus
from lexigram.result import Ok, Result


class ServerStatusWidgetHandler:
    """Handler for the server_status widget.

    Fetches server status information and uptime.
    For now, returns reasonable defaults (TODO: integrate with actual server stats).
    """

    async def get_data(
        self, params: WidgetParams
    ) -> Result[HealthCheckPayload, AdminError]:
        """Fetch server status data.

        Args:
            params: Widget request parameters (unused for this widget).

        Returns:
            Result containing HealthCheckPayload with server status.
        """
        is_running = True
        uptime_seconds = 3600  # 1 hour
        server_version = "1.0.0"
        return Ok(
            HealthCheckPayload(
                status=HealthStatus.HEALTHY if is_running else HealthStatus.UNHEALTHY,
                component="HTTP Server",
                detail=f"v{server_version}, up {uptime_seconds}s",
            )
        )


__all__ = ["ServerStatusWidgetHandler"]
