"""Widget viewmodels for web admin dashboard.

Frozen dataclasses representing the data contract for widget rendering.
These are passed to Jinja2 templates for HTML generation.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ServerStatusViewModel:
    """Data model for the server_status widget.

    Attributes:
        is_running: Whether the HTTP server is accepting connections.
        uptime_seconds: Seconds the server has been running.
        server_version: Version of the server/framework.
    """

    is_running: bool
    uptime_seconds: int
    server_version: str


@dataclass(frozen=True)
class ActiveConnectionsViewModel:
    """Data model for the active_connections widget.

    Attributes:
        active: Current number of open connections.
        peak: Peak number of connections seen.
        max_allowed: Maximum allowed concurrent connections.
    """

    active: int
    peak: int
    max_allowed: int


@dataclass(frozen=True)
class RequestRateViewModel:
    """Data model for the request_rate widget.

    Attributes:
        requests_per_second: Current request rate.
        total_requests: Total number of requests processed.
        error_rate_pct: Error rate as a percentage.
    """

    requests_per_second: float
    total_requests: int
    error_rate_pct: float


__all__ = [
    "ServerStatusViewModel",
    "ActiveConnectionsViewModel",
    "RequestRateViewModel",
]
