"""CLI shell context factories for lexigram-events."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.events import EventBusProtocol

if TYPE_CHECKING:
    from lexigram.contracts.core.di import ContainerResolverProtocol


async def provide_event_bus(container: ContainerResolverProtocol) -> EventBusProtocol:
    """Provide event bus for interactive shell use.

    Args:
        container: Booted DI container.

    Returns:
        The resolved EventBus instance.
    """
    return await container.resolve(EventBusProtocol)
