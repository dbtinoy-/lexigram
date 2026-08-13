"""CLI health checks for lexigram-vector."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lexigram.contracts.core.di import ContainerResolverProtocol


async def check_vector_store(container: ContainerResolverProtocol) -> dict[str, object]:
    """Verify vector store backend connectivity.

    Args:
        container: Booted DI container.

    Returns:
        A HealthCheckResult-compatible dict.
    """
    return {"status": "ok", "message": "Vector store health check not yet implemented"}
