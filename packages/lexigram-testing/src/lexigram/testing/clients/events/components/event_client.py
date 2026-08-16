"""Testing client for lexigram-events event operations."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from lexigram.events import Event, EventBusProtocol, EventHandlerProtocol
from lexigram.testing import TestEnvironment


class EventTestClient:
    """Testing client for lexigram-events event operations.

    Provides high-level testing utilities for event publishing, subscription,
    and handler testing.

    Example:
        >>> async with EventTestBed() as bed:
        ...     client = EventTestClient(bed)
        ...     await client.publish_event(UserCreatedEvent(user_id="123"))
        ...     events = await client.get_published_events()
        ...     assert len(events) == 1
    """

    def __init__(self, test_bed: TestEnvironment):
        """Initialize the event test client.

        Args:
            test_bed: The test bed providing event infrastructure
        """
        self.test_bed = test_bed
        self._event_bus: EventBusProtocol | None = None
        self._published_events: list[Event] = []
        self._handler_calls: dict[str, list[Any]] = {}

    @property
    def event_bus(self) -> EventBusProtocol:
        """Get the event bus from the test bed."""
        if self._event_bus is None:
            self._event_bus = getattr(self.test_bed, "_event_bus", None)
        return cast("EventBusProtocol", self._event_bus)

    async def publish_event(
        self,
        event: Event,
        expected_handlers: int | None = None,
    ) -> None:
        """Publish an event and track it.

        Args:
            event: The event to publish
            expected_handlers: Expected number of handlers that should process the event
        """
        # Track the event
        self._published_events.append(event)

        # Publish through the bus
        await self.event_bus.publish(event)

        # Check handler expectations if specified
        if expected_handlers is not None:
            handler_count = len(self.event_bus._subscribers.get(type(event), []))  # type: ignore[attr-defined]
            if handler_count != expected_handlers:
                raise AssertionError(
                    f"Expected {expected_handlers} handlers for "
                    f"{type(event).__name__}; found {handler_count}",
                )

    async def subscribe_handler(
        self,
        event_type: type[Event],
        handler: EventHandlerProtocol | Callable,
    ) -> None:
        """Subscribe an event handler.

        Args:
            event_type: The event type to subscribe to
            handler: The handler function or class
        """
        self.event_bus.subscribe(event_type, handler)  # type: ignore[arg-type]

    async def unsubscribe_handler(
        self,
        event_type: type[Event],
        handler: EventHandlerProtocol | Callable,
    ) -> bool:
        """Unsubscribe an event handler.

        Args:
            event_type: The event type to unsubscribe from
            handler: The handler to remove

        Returns:
            True if handler was unsubscribed
        """
        return self.event_bus.unsubscribe(event_type, handler)  # type: ignore[func-returns-value,return-value,arg-type]

    def get_published_events(
        self,
        event_type: type[Event] | None = None,
    ) -> list[Event]:
        """Get all published events, optionally filtered by type.

        Args:
            event_type: Filter by event type

        Returns:
            List of published events
        """
        if event_type:
            return [e for e in self._published_events if isinstance(e, event_type)]
        return self._published_events.copy()

    def assert_event_published(
        self,
        event_type: type[Event],
        expected_count: int = 1,
        **filters: Any,
    ) -> list[Event]:
        """Assert that events of a type were published.

        Args:
            event_type: The event type to check
            expected_count: Expected number of events
            **filters: Additional filters for event attributes

        Returns:
            List of matching events
        """
        events = self.get_published_events(event_type)

        # Apply filters
        if filters:
            events = [
                event
                for event in events
                if all(getattr(event, k, None) == v for k, v in filters.items())
            ]

        if len(events) != expected_count:
            raise AssertionError(
                f"Expected {expected_count} {event_type.__name__} events, "
                f"found {len(events)}",
            )

        return events

    def assert_no_events_published(self, event_type: type[Event] | None = None) -> None:
        """Assert that no events were published.

        Args:
            event_type: Specific event type to check, or None for all events
        """
        events = self.get_published_events(event_type)
        if events:
            event_names = [type(e).__name__ for e in events]
            raise AssertionError(f"Unexpected events published: {event_names}")

    async def test_event_handler(
        self,
        event: Event,
        handler: EventHandlerProtocol | Callable,
        expected_calls: int = 1,
    ) -> None:
        """Test an event handler with a specific event.

        Args:
            event: The event to test with
            handler: The handler to test
            expected_calls: Expected number of handler calls
        """
        # Track handler calls
        handler_key = (
            f"{handler.__class__.__name__}.{handler.__name__}"
            if hasattr(handler, "__name__")
            else str(handler)
        )
        if handler_key not in self._handler_calls:
            self._handler_calls[handler_key] = []

        # Subscribe handler temporarily
        event_type = type(event)
        self.event_bus.subscribe(event_type, handler)  # type: ignore[arg-type]

        try:
            # Publish event
            await self.publish_event(event)

            # Check if handler was called expected number of times
            calls = self._handler_calls.get(handler_key, [])
            if len(calls) != expected_calls:
                raise AssertionError(
                    f"Expected handler {handler_key} to be called "
                    f"{expected_calls} times; was called {len(calls)} times",
                )

        finally:
            # Cleanup
            self.event_bus.unsubscribe(event_type, handler)  # type: ignore[arg-type]

    def clear_published_events(self) -> None:
        """Clear the published events history."""
        self._published_events.clear()

    def get_handler_calls(self, handler: Any) -> list[Any]:
        """Get calls made to a specific handler.

        Args:
            handler: The handler to check

        Returns:
            List of calls made to the handler
        """
        handler_key = (
            f"{handler.__class__.__name__}.{handler.__name__}"
            if hasattr(handler, "__name__")
            else str(handler)
        )
        return self._handler_calls.get(handler_key, []).copy()
