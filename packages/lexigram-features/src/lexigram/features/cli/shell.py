"""CLI shell context factories for lexigram-features."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lexigram.contracts.core.di import ContainerResolverProtocol


async def provide_flag_manager(container: ContainerResolverProtocol) -> object:
    """Provide FlagManager for interactive shell use.

    Args:
        container: Booted DI container.

    Returns:
        The resolved FlagManager instance.
    """
    from lexigram.features.manager import FlagManager

    return await container.resolve(FlagManager)
