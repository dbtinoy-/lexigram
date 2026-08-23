"""CLI shell context factories for lexigram-cache."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from lexigram.contracts.infra.cache.protocols import CacheBackendProtocol

if TYPE_CHECKING:
    from lexigram.contracts.core.di import ContainerResolverProtocol


async def provide_cache(
    container: ContainerResolverProtocol,
) -> CacheBackendProtocol:
    """Provide cache backend for interactive shell use.

    Args:
        container: Booted DI container.

    Returns:
        The resolved CacheBackendProtocol instance.
    """
    return cast(
        "CacheBackendProtocol",
        await container.resolve(CacheBackendProtocol),
    )
