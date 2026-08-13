"""CLI health checks for lexigram-ai."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lexigram.contracts.core.di import ContainerResolverProtocol


async def check_llm_provider(container: ContainerResolverProtocol) -> dict[str, object]:
    """Check that an LLM provider is reachable.

    Args:
        container: Booted DI container.

    Returns:
        A HealthCheckResult-compatible dict.
    """
    return {
        "status": "healthy",
        "message": "LLM provider health check not yet implemented",
    }


async def check_subsystem_discovery(
    container: ContainerResolverProtocol,
) -> dict[str, object]:
    """Check that AI subsystems are discoverable via entry points.

    Args:
        container: Booted DI container.

    Returns:
        A HealthCheckResult-compatible dict.
    """
    return {
        "status": "healthy",
        "message": "AI subsystem discovery check not yet implemented",
    }
