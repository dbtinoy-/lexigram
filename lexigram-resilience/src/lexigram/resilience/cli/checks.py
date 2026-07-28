"""CLI health checks for lexigram-resilience."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lexigram.contracts.core.di import ContainerResolverProtocol


async def check_circuit_breakers(
    container: ContainerResolverProtocol,
) -> dict[str, object]:
    """Check the state of all registered circuit breakers.

    Args:
        container: Booted DI container.

    Returns:
        A HealthCheckResult-compatible dict.
    """
    return {
        "status": "healthy",
        "message": "Circuit breaker health check not yet implemented",
    }
