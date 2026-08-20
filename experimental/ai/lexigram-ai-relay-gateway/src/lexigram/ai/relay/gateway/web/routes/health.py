"""Health and readiness route for the relay gateway web layer.

``GET /health`` reports process liveness and dependency health without
authentication: probe traffic from load balancers and orchestrators
cannot present tenant credentials.  The payload aggregates the converter
registry check and one check per configured channel (from
``RelayHealthService``) into ``ok | degraded | down``, returning HTTP
200 for ``ok``/``degraded`` and 503 for ``down``.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from time import monotonic
from typing import Any, TypeAlias

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from lexigram.ai.relay.gateway.operations.health import RelayHealthService
from lexigram.contracts.ai.relay import RelayChannelHealth, RelayGatewayError
from lexigram.logging import get_logger
from lexigram.primitives import clock

__all__ = ["HEALTH_ROUTE_PATH", "ResolveRelayHealth", "health_endpoint"]

logger = get_logger(__name__)

HEALTH_ROUTE_PATH = "/health"
"""Path of the unauthenticated health route."""

_PACKAGE = "lexigram-ai-relay-gateway"
"""Distribution name used for version reporting."""

ResolveRelayHealth: TypeAlias = Callable[
    [Request], Awaitable[RelayHealthService | None]
]
"""Resolver of the health service from a Starlette request."""

_CHECK_OK = "ok"
_CHECK_DEGRADED = "degraded"
_CHECK_DOWN = "down"

_CHANNEL_STATUS: dict[str, str] = {
    "healthy": _CHECK_OK,
    "degraded": _CHECK_DEGRADED,
    "unavailable": _CHECK_DOWN,
    "failed": _CHECK_DOWN,
}
"""Relay channel snapshot status to health-check status mapping."""


def _gateway_version() -> str:
    """Return the installed gateway distribution version.

    Returns:
        The version string, or ``"unknown"`` when the distribution is
        not installed as metadata.
    """
    try:
        return version(_PACKAGE)
    except PackageNotFoundError:
        return "unknown"


def _channel_check(snapshot: RelayChannelHealth) -> dict[str, Any]:
    """Map one channel snapshot to the health check payload entry.

    Args:
        snapshot: The channel health snapshot.

    Returns:
        The ``{"name", "status", "latency_ms"}`` entry; ``latency_ms``
        is omitted when the snapshot carries no latency signal.
    """
    check: dict[str, Any] = {
        "name": snapshot.channel,
        "status": _CHANNEL_STATUS.get(snapshot.status, _CHECK_DOWN),
    }
    if snapshot.latency_ms_p50 is not None:
        check["latency_ms"] = round(snapshot.latency_ms_p50)
    return check


def _report(
    status: str, checks: list[dict[str, Any]], checked_at: datetime
) -> Response:
    """Build the health JSON response.

    Args:
        status: Aggregate status, ``ok``/``degraded``/``down``.
        checks: Per-dependency health entries.
        checked_at: When the snapshot was taken.

    Returns:
        A JSON response; ``down`` maps to HTTP 503.
    """
    return JSONResponse(
        status_code=503 if status == _CHECK_DOWN else 200,
        content={
            "status": status,
            "version": _gateway_version(),
            "timestamp": checked_at.isoformat(),
            "checks": checks,
        },
        headers={"cache-control": "no-store"},
    )


async def health_endpoint(
    resolve_health: ResolveRelayHealth,
    request: Request,
) -> Response:
    """Serve the aggregate health and readiness payload.

    Runs the registry check and one check per configured channel, each
    bounded by the health service.  An unresolvable health service (for
    example a host app without the gateway provider registered) reports
    ``down`` with no checks rather than failing the probe.

    Args:
        resolve_health: Async callable resolving the health service from
            the request, or ``None`` when the service is unavailable.
        request: The Starlette request being served.

    Returns:
        The health JSON response (HTTP 200 when healthy or degraded,
        HTTP 503 when down).
    """
    checks: list[dict[str, Any]] = []
    checked_at = clock.now()
    service = await resolve_health(request)
    if service is None:
        logger.warning(
            "relay_gateway_health_unavailable",
            reason="health_service_not_resolved",
        )
        return _report(_CHECK_DOWN, checks, checked_at)

    started = monotonic()
    try:
        await service.registry_diagnostics()
        registry_status = _CHECK_OK
    except RelayGatewayError as error:
        logger.warning(
            "relay_gateway_health_registry_failed",
            error_code=error.code,
        )
        registry_status = _CHECK_DOWN
    except Exception:  # noqa: BLE001 - a broken probe must not crash /health
        logger.exception("relay_gateway_health_registry_error")
        registry_status = _CHECK_DOWN
    checks.append(
        {
            "name": "registry",
            "status": registry_status,
            "latency_ms": round((monotonic() - started) * 1000),
        }
    )

    try:
        snapshots = await service.channel_health()
    except Exception:  # noqa: BLE001 - a broken probe must not crash /health
        logger.exception("relay_gateway_health_channels_error")
        snapshots = ()
    checks.extend(_channel_check(snapshot) for snapshot in snapshots)

    if any(check["status"] == _CHECK_DOWN for check in checks):
        status = _CHECK_DOWN
    elif any(check["status"] == _CHECK_DEGRADED for check in checks):
        status = _CHECK_DEGRADED
    else:
        status = _CHECK_OK
    return _report(status, checks, checked_at)
