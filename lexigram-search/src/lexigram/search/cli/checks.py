"""CLI health checks for lexigram-search."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lexigram.contracts.core.di import ContainerResolverProtocol


async def check_search_backend(
    container: ContainerResolverProtocol,
) -> dict[str, object]:
    """Verify search backend connectivity.

    Args:
        container: Booted DI container.

    Returns:
        A HealthCheckResult-compatible dict.
    """
    return {
        "status": "ok",
        "message": "Search backend health check not yet implemented",
    }
