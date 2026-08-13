"""Admin health surface for the relay gateway.

Defines the aggregate channel health check and its rendering, including
the worst-case status aggregation over per-channel snapshots.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, cast

from lexigram.ai.relay.gateway.operations.health import RelayHealthService
from lexigram.contracts.admin.errors import HealthCheckNotFoundError
from lexigram.contracts.admin.health_payload import HealthCheckPayload
from lexigram.contracts.admin.types import AdminHealthDefinition
from lexigram.contracts.ai.relay import RelayChannelHealth
from lexigram.contracts.core.health import HealthStatus
from lexigram.result import Err, Ok, Result

if TYPE_CHECKING:
    from lexigram.contracts.admin.errors import AdminError

__all__ = ["HEALTH_DEFS", "render_health_check"]

HEALTH_DEFS: tuple[AdminHealthDefinition, ...] = (
    AdminHealthDefinition(
        name="relay.channels",
        contributor="relay-gateway",
        component="Relay Channels",
        check_endpoint="/admin/relay-gateway/health/channels",
        description="Aggregates per-channel probe status.",
    ),
)


async def render_health_check(
    health: RelayHealthService | None,
    check_name: str,
) -> Result[HealthCheckPayload, AdminError]:
    """Render the aggregate channel health check.

    Args:
        health: Resolved health service, or None when unavailable at boot.
        check_name: Name of the health check; only ``relay.channels``
            is served.

    Returns:
        Ok(HealthCheckPayload) with the aggregate snapshot; Err when
        the check is unknown or the health service is unavailable.
    """
    if check_name != "relay.channels":
        not_found: Result[HealthCheckPayload, AdminError] = cast(
            "Result[HealthCheckPayload, AdminError]",
            Err(HealthCheckNotFoundError("relay-gateway", check_name)),
        )
        return not_found
    if health is None:
        unavailable: Result[HealthCheckPayload, AdminError] = cast(
            "Result[HealthCheckPayload, AdminError]",
            Err(HealthCheckNotFoundError("relay-gateway", check_name)),
        )
        return unavailable
    snapshots = await health.channel_health()
    parts = [f"{snap.channel}: {snap.status}" for snap in snapshots]
    detail = ", ".join(parts) if parts else "no channels configured"
    return Ok(
        HealthCheckPayload(
            status=_aggregate_channel_status(snapshots),
            component="Relay Channels",
            detail=detail,
        )
    )


def _aggregate_channel_status(
    snapshots: Sequence[RelayChannelHealth],
) -> HealthStatus:
    """Map channel snapshots to a worst-case HealthStatus.

    Any ``failed``/``unavailable`` channel makes the aggregate
    UNHEALTHY; otherwise any ``degraded`` channel makes it DEGRADED;
    with no channels the state is UNKNOWN.

    Args:
        snapshots: Per-channel health snapshots.

    Returns:
        The worst-case HealthStatus across the snapshots.
    """
    if not snapshots:
        return HealthStatus.UNKNOWN
    if any(snap.status in ("unavailable", "failed") for snap in snapshots):
        return HealthStatus.UNHEALTHY
    if any(snap.status == "degraded" for snap in snapshots):
        return HealthStatus.DEGRADED
    return HealthStatus.HEALTHY
