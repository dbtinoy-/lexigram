"""CLI shell context factories for lexigram-resilience."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.resilience.protocols import (  # type: ignore[import-untyped]
    CircuitBreakerProtocol,
)

if TYPE_CHECKING:
    from lexigram.contracts.core.di import ContainerResolverProtocol


async def provide_resilience_pipeline(
    container: ContainerResolverProtocol,
) -> CircuitBreakerProtocol:
    """Provide the resilience pipeline for interactive shell use.

    Args:
        container: Booted DI container.

    Returns:
        The resolved resilience pipeline instance.
    """
    return await container.resolve(CircuitBreakerProtocol)
