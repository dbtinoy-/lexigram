"""Adapter that delegates admin event dispatch to ``lexigram-events``.

When ``lexigram-events`` is installed, ``AdminEventBusAdapter`` wraps
``lexigram.events.buses.event.EventBusImpl`` for pub/sub event dispatch
with middleware, retry, and dead letter queue support.  When not installed,
it falls back to a simple synchronous dispatcher.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

try:
    from lexigram.events.buses.event import DispatchResult as _DispatchResult
    from lexigram.events.buses.event import EventBusImpl as _EventBusImpl
    from lexigram.events.messages.event import Event as _Event

    _HAS_EVENTS = True
except ImportError:  # noqa: F841
    _HAS_EVENTS = False
    _EventBusImpl = object  # type: ignore[assignment,misc]
    _DispatchResult = object  # type: ignore[assignment,misc]
    _Event = object  # type: ignore[assignment,misc]


class _SimpleDispatcher:
    """Fallback in-process event dispatcher when lexigram-events is not installed."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[..., Any]]] = {}

    def subscribe(self, event_type: str, handler: Callable[..., Any]) -> None:
        """Register a handler for an event type."""
        self._handlers.setdefault(event_type, []).append(handler)

    async def publish(self, event: Any) -> None:
        """Dispatch an event to all registered handlers."""
        event_type = type(event).__name__
        for handler in self._handlers.get(event_type, []):
            try:
                result = handler(event)
                if hasattr(result, "__await__"):
                    await result
            except Exception:  # noqa: BLE001
                pass


class AdminEventBusAdapter:
    """Bridge between admin's event dispatch and ``lexigram-events``'s ``EventBusImpl``.

    Usage::

        bus = AdminEventBusAdapter(event_bus=real_bus)
        await bus.publish(AdminStarted(version="1.0"))
    """

    def __init__(
        self,
        event_bus: Any | None = None,
    ) -> None:
        self._bus = event_bus or _SimpleDispatcher()

    async def publish(self, event: Any) -> Any:
        """Publish an event to all registered handlers.

        Args:
            event: The event instance to publish.

        Returns:
            Dispatch result from lexigram-events if available, else None.
        """
        if self._bus is None:
            return None
        try:
            return await self._bus.publish(event)
        except Exception:  # noqa: BLE001
            return None

    def subscribe(self, event_type: str, handler: Callable[..., Any]) -> None:
        """Register a handler for a given event type.

        Args:
            event_type: The event type name to subscribe to.
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


__all__ = ["AdminEventBusAdapter"]
