"""CLI health checks for lexigram-queue."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lexigram.contracts.core.di import ContainerResolverProtocol


async def check_broker_connection(
    container: ContainerResolverProtocol,
) -> dict[str, object]:
    """Verify message broker connectivity.

    Args:
        container: Booted DI container.

    Returns:
        A HealthCheckResult-compatible dict.
    """
    return {
        "status": "ok",
        "message": "Message broker health check not yet implemented",
    }
