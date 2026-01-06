"""CLI shell context factories for lexigram-monitor."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.monitor.backends.base import (  # type: ignore[import-untyped]
    MetricsBackend,
)

if TYPE_CHECKING:
    from lexigram.contracts.core.di import ContainerResolverProtocol


async def provide_metrics(container: ContainerResolverProtocol) -> MetricsBackend:
    """Provide metrics backend for interactive shell use.

    Args:
        container: Booted DI container.

    Returns:
        The resolved metrics backend instance.
    """
    return await container.resolve(MetricsBackend)
