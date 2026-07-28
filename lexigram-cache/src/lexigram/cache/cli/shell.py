"""CLI shell context factories for lexigram-cache."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.cache import CacheBackend  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from lexigram.contracts.core.di import ContainerResolverProtocol


async def provide_cache(container: ContainerResolverProtocol) -> CacheBackend:
    """Provide cache backend for interactive shell use.

    Args:
        container: Booted DI container.

    Returns:
        The resolved CacheBackend instance.
    """
    return await container.resolve(CacheBackend)
