"""Adapter that delegates admin event dispatch to an ``EventBusProtocol`` bus.

``AdminEventBusAdapter`` wraps a container-provided event bus (typically a
``lexigram-events`` implementation) for pub/sub event dispatch.  When no
bus is configured, it falls back to a simple in-process dispatcher.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.contracts.events import EventBusProtocol

if TYPE_CHECKING:
    from collections.abc import Callable


class _SimpleDispatcher:
    """Fallback in-process event dispatcher when no bus is configured."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[..., Any]]] = {}
        self._global_handlers: list[Callable[..., Any]] = []

    def subscribe(self, event_type: str | None, handler: Callable[..., Any]) -> None:
        """Register a handler for an event type."""
        if event_type is None:
            self._global_handlers.append(handler)
            return
        self._handlers.setdefault(event_type, []).append(handler)

    async def publish(self, event: Any) -> None:
        """Dispatch an event to all registered handlers."""
        event_type = type(event).__name__
        for handler in [*self._global_handlers, *self._handlers.get(event_type, [])]:
            try:
                result = handler(event)
                if hasattr(result, "__await__"):
                    await result
            except Exception:  # noqa: BLE001
                pass


class AdminEventBusAdapter:
    """Bridge between admin's event dispatch and an ``EventBusProtocol`` bus.

    Usage::

        bus = AdminEventBusAdapter(event_bus=real_bus)
        await bus.publish(AdminStarted(version="1.0"))
    """

    def __init__(
        self,
        event_bus: EventBusProtocol | None = None,
    ) -> None:
        self._bus: Any = event_bus or _SimpleDispatcher()

    async def publish(self, event: Any) -> Any:
        """Publish an event to all registered handlers.

        Args:
            event: The event instance to publish.

        Returns:
            Dispatch result from the bus if available, else None.
        """
        if self._bus is None:
            return None
        try:
            return await self._bus.publish(event)
        except Exception:  # noqa: BLE001
            return None

    def subscribe(self, event_type: str | None, handler: Callable[..., Any]) -> None:
        """Register a handler for a given event type.

        Args:
            event_type: The event type name to subscribe to; ``None``
                registers a global handler on the fallback dispatcher.
            handler: Callable that accepts the event.
        """
        if self._bus is not None and hasattr(self._bus, "subscribe"):
            self._bus.subscribe(event_type, handler)

    async def publish_many(self, events: list[Any]) -> list[Any]:
        """Publish multiple events in sequence.

        Args:
            events: List of event instances.

        Returns:
            List of dispatch results.
        """
        if self._bus is None:
            return []
        results: list[Any] = []
        for event in events:
            result = await self.publish(event)
            results.append(result)
        return results

    def stream(self) -> Any:
        """Return a hot stream of admin events from the configured bus.

        Returns:
            An ``EventStream[Any]`` from ``lexigram.reactive`` fed by the
            bus (or the fallback dispatcher) through a shared Subject.
            Live events only; use ``lexigram.events.reactive.from_bus``
            for catchup replay from an event store.
        """
        from lexigram.reactive import Subject

        subject = Subject[Any]()

        async def _handler(event: Any) -> None:
            await subject.publish(event)

        self.subscribe(None, _handler)
        return subject


__all__ = ["AdminEventBusAdapter"]
