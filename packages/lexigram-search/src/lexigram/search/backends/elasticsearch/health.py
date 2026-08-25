"""Health-check operation for the Elasticsearch backend."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.core import HealthCheckResult, HealthStatus
from lexigram.logging import get_logger

logger = get_logger(__name__)


async def check_cluster_health(
    client: Any,
    hosts: list[str],
) -> HealthCheckResult:
    """Check Elasticsearch cluster health.

    Args:
        client: Elasticsearch client.
        hosts: Configured host list (reported in the result details).

    Returns:
        Structured health check result with cluster status details.
    """
    try:
        info = await client.info()
        cluster_name = info.get("cluster_name", "unknown")
        version = info.get("version", {}).get("number", "unknown")
        return HealthCheckResult(
            component="elasticsearch",
            status=HealthStatus.HEALTHY,
            details={
                "backend": "elasticsearch",
                "cluster_name": cluster_name,
                "version": version,
                "hosts": hosts,
            },
        )
    except Exception as e:  # noqa: BLE001 — health check boundary
        logger.debug("Elasticsearch health check failed: %s", e)
        return HealthCheckResult(
            component="elasticsearch",
            status=HealthStatus.UNHEALTHY,
            error=str(e),
            details={"backend": "elasticsearch", "hosts": hosts},
        )
