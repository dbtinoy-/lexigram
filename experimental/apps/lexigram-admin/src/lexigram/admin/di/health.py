"""Health aggregation for the admin bundle provider."""

from __future__ import annotations

import asyncio
from typing import Any

from lexigram.contracts.core.health import HealthCheckResult, HealthStatus


async def aggregate_sub_provider_health(
    sub_providers: list[Any],
    mount_failures: dict[str, str],
    timeout: float = 5.0,
) -> HealthCheckResult:
    """Aggregate health from all admin sub-providers.

    The worst observed status wins (UNHEALTHY > DEGRADED > UNKNOWN >
    HEALTHY); recorded mount failures degrade an otherwise healthy result.

    Args:
        sub_providers: Sub-providers exposing ``health_check(timeout)``.
        mount_failures: Mount-time failure map recorded by the provider.
        timeout: Per-sub-provider health check timeout.

    Returns:
        Aggregate HealthCheckResult for the ``admin`` component.
    """
    worst = HealthStatus.HEALTHY
    details: dict[str, Any] = {}
    for sp in sub_providers:
        maybe = sp.health_check(timeout)
        result: HealthCheckResult = await maybe if asyncio.iscoroutine(maybe) else maybe
        details[result.component] = result.status.value
        if result.status == HealthStatus.UNHEALTHY:
            worst = HealthStatus.UNHEALTHY
        elif result.status == HealthStatus.DEGRADED and worst != HealthStatus.UNHEALTHY:
            worst = HealthStatus.DEGRADED
        elif result.status == HealthStatus.UNKNOWN and worst == HealthStatus.HEALTHY:
            worst = HealthStatus.UNKNOWN

    if mount_failures and worst != HealthStatus.UNHEALTHY:
        worst = HealthStatus.DEGRADED
        details["mount_failures"] = dict(mount_failures)

    return HealthCheckResult(
        component="admin",
        status=worst,
        message=f"Admin bundle: {worst.value}",
        details=details,
    )


__all__ = ["aggregate_sub_provider_health"]
