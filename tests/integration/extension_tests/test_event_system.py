"""Tests for the hardened event system (Phase 5).

Covers:
- InMemoryEventBus subscribe/publish (existing baseline)
- unsubscribe behaviour
- middleware chain execution
- middleware ordering
- protocol compliance (EventBusProtocol, EventMiddlewareProtocol)
- EventProvider DI registration
- error propagation from handlers
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from lexigram.contracts.domain import DomainEvent
from lexigram.contracts.events import EventBusProtocol, EventMiddlewareProtocol
from lexigram.testing.memory.event_bus import InMemoryEventBus

# ---------------------------------------------------------------------------
# Test events
# ---------------------------------------------------------------------------


class OrderCreated(DomainEvent):
    """Test event for order creation."""

    order_id: str


class OrderCancelled(DomainEvent):
    """Test event for order cancellation."""

    order_id: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class ObjectHandler:
    """Object-style handler with .handle() method."""

    def __init__(self) -> None:
        self.events: list[DomainEvent] = []

    async def handle(self, event: DomainEvent) -> None:
        self.events.append(event)


# ---------------------------------------------------------------------------
# Tests: Basic subscribe / publish
# ---------------------------------------------------------------------------


class TestSubscribePublish:
    """Verify baseline subscribe/publish still works."""

    @pytest.mark.asyncio
    async def test_callable_handler(self) -> None:
        """Async callable handlers receive published events."""
        received: list[DomainEvent] = []

        async def handler(event: OrderCreated) -> None:
            received.append(event)

        bus = InMemoryEventBus()
        bus.subscribe(OrderCreated, handler)
        event = OrderCreated(order_id="1")
        await bus.publish(event)

        assert received == [event]

    @pytest.mark.asyncio
    async def test_object_handler(self) -> None:
        """Object handlers with .handle() method receive published events."""
        handler = ObjectHandler()
        bus = InMemoryEventBus()
        bus.subscribe(OrderCreated, handler)
        event = OrderCreated(order_id="2")
        await bus.publish(event)

        assert handler.events == [event]

    @pytest.mark.asyncio
    async def test_no_handlers_is_noop(self) -> None:
        """Publishing with no subscribers does not raise."""
        bus = InMemoryEventBus()
        await bus.publish(OrderCreated(order_id="3"))

    @pytest.mark.asyncio
    async def test_handlers_only_receive_subscribed_type(self) -> None:
        """Handlers are only triggered by the event type they subscribed to."""
        received: list[str] = []

        async def handler(event: OrderCreated) -> None:
            received.append(event.order_id)

        bus = InMemoryEventBus()
        bus.subscribe(OrderCreated, handler)
        await bus.publish(OrderCancelled(order_id="x"))

        assert received == []


# ---------------------------------------------------------------------------
# Tests: Unsubscribe
# ---------------------------------------------------------------------------


class TestUnsubscribe:
    """Verify unsubscribe correctly removes handlers."""

    @pytest.mark.asyncio
    async def test_unsubscribe_callable(self) -> None:
        """After unsubscribe, a callable handler no longer receives events."""
        received: list[str] = []

        async def handler(event: OrderCreated) -> None:
            received.append(event.order_id)

        bus = InMemoryEventBus()
        bus.subscribe(OrderCreated, handler)
        bus.unsubscribe(OrderCreated, handler)

        await bus.publish(OrderCreated(order_id="gone"))
        assert received == []

    @pytest.mark.asyncio
    async def test_unsubscribe_object_handler(self) -> None:
        """After unsubscribe, an object handler no longer receives events."""
        handler = ObjectHandler()
        bus = InMemoryEventBus()
        bus.subscribe(OrderCreated, handler)
        bus.unsubscribe(OrderCreated, handler)

        await bus.publish(OrderCreated(order_id="gone"))
        assert handler.events == []

    @pytest.mark.asyncio
    async def test_unsubscribe_unknown_handler_is_noop(self) -> None:
        """Unsubscribing a handler that was never registered does not raise."""
        async def handler(event: OrderCreated) -> None:
            pass

        bus = InMemoryEventBus()
        bus.unsubscribe(OrderCreated, handler)  # should not raise

    @pytest.mark.asyncio
    async def test_unsubscribe_unknown_event_type_is_noop(self) -> None:
        """Unsubscribing from an event type with no subscriptions is a no-op."""
        bus = InMemoryEventBus()
        bus.unsubscribe(OrderCreated, ObjectHandler())  # should not raise

    @pytest.mark.asyncio
    async def test_unsubscribe_leaves_other_handlers(self) -> None:
        """Unsubscribing one handler does not affect other handlers for same type."""
        results: list[str] = []

        async def h1(event: OrderCreated) -> None:
            results.append("h1")

        async def h2(event: OrderCreated) -> None:
            results.append("h2")

        bus = InMemoryEventBus()
        bus.subscribe(OrderCreated, h1)
        bus.subscribe(OrderCreated, h2)
        bus.unsubscribe(OrderCreated, h1)

        await bus.publish(OrderCreated(order_id="partial"))
        assert results == ["h2"]


# ---------------------------------------------------------------------------
# Tests: Middleware
# ---------------------------------------------------------------------------


class TestMiddleware:
    """Verify middleware wraps handler execution correctly."""

    @pytest.mark.asyncio
    async def test_single_middleware(self) -> None:
        """A single middleware wraps handler invocation."""
        trace: list[str] = []

        async def mw(event: Any, next_handler: Any) -> None:
            trace.append("before")
            await next_handler(event)
            trace.append("after")

        async def handler(event: OrderCreated) -> None:
            trace.append("handler")

        bus = InMemoryEventBus()
        bus.add_middleware(mw)
        bus.subscribe(OrderCreated, handler)
        await bus.publish(OrderCreated(order_id="mw"))

        assert trace == ["before", "handler", "after"]

    @pytest.mark.asyncio
    async def test_middleware_ordering(self) -> None:
        """Middleware executes in registration order (outermost first)."""
        trace: list[str] = []

        async def mw1(event: Any, next_handler: Any) -> None:
            trace.append("mw1:before")
            await next_handler(event)
            trace.append("mw1:after")

        async def mw2(event: Any, next_handler: Any) -> None:
            trace.append("mw2:before")
            await next_handler(event)
            trace.append("mw2:after")

        async def handler(event: OrderCreated) -> None:
            trace.append("handler")

        bus = InMemoryEventBus()
        bus.add_middleware(mw1)
        bus.add_middleware(mw2)
        bus.subscribe(OrderCreated, handler)
        await bus.publish(OrderCreated(order_id="order"))

        assert trace == [
            "mw1:before",
            "mw2:before",
            "handler",
            "mw2:after",
            "mw1:after",
        ]

    @pytest.mark.asyncio
    async def test_middleware_can_short_circuit(self) -> None:
        """Middleware can prevent handler execution by not calling next_handler."""
        handler_called = False

        async def blocking_mw(event: Any, next_handler: Any) -> None:
            pass  # intentionally not calling next_handler

        async def handler(event: OrderCreated) -> None:
            nonlocal handler_called
            handler_called = True

        bus = InMemoryEventBus()
        bus.add_middleware(blocking_mw)
        bus.subscribe(OrderCreated, handler)
        await bus.publish(OrderCreated(order_id="blocked"))

        assert handler_called is False

    @pytest.mark.asyncio
    async def test_no_middleware_dispatches_directly(self) -> None:
        """Without middleware, handlers receive events directly."""
        received: list[str] = []

        async def handler(event: OrderCreated) -> None:
            received.append(event.order_id)

        bus = InMemoryEventBus()
        bus.subscribe(OrderCreated, handler)
        await bus.publish(OrderCreated(order_id="direct"))

        assert received == ["direct"]


# ---------------------------------------------------------------------------
# Tests: Protocol compliance
# ---------------------------------------------------------------------------


class TestProtocolCompliance:
    """Verify InMemoryEventBus satisfies contract protocols."""

    def test_satisfies_event_bus_protocol(self) -> None:
        """InMemoryEventBus is a structural subtype of EventBusProtocol."""
        bus = InMemoryEventBus()
        assert isinstance(bus, EventBusProtocol)

    def test_middleware_callable_satisfies_protocol(self) -> None:
        """A plain async callable satisfying the middleware shape passes protocol check."""

        class MyMiddleware:
            async def __call__(self, event: Any, next_handler: Any) -> None:
                await next_handler(event)

        mw = MyMiddleware()
        assert isinstance(mw, EventMiddlewareProtocol)


# ---------------------------------------------------------------------------
# Tests: MemoryProvider
# ---------------------------------------------------------------------------


class TestMemoryProvider:
    """Verify MemoryProvider registers correct bindings."""

    def test_provider_name(self) -> None:
        """MemoryProvider has name 'memory'."""
        from lexigram.testing.memory.di.provider import MemoryProvider

        provider = MemoryProvider()
        assert provider.name == "memory"

    @pytest.mark.asyncio
    async def test_register_binds_event_bus(self) -> None:
        """MemoryProvider registers EventBusProtocol singleton."""
        from lexigram.testing.memory.di.provider import MemoryProvider

        provider = MemoryProvider()
        container = MagicMock()
        await provider.register(container)

        calls = container.singleton.call_args_list
        bound_abstracts = [c.args[0] for c in calls]
        assert EventBusProtocol in bound_abstracts

    @pytest.mark.asyncio
    async def test_register_binds_domain_event_publisher(self) -> None:
        """MemoryProvider registers DomainEventPublisherProtocol singleton."""
        from lexigram.contracts.events import DomainEventPublisherProtocol
        from lexigram.testing.memory.di.provider import MemoryProvider

        provider = MemoryProvider()
        container = MagicMock()
        await provider.register(container)

        calls = container.singleton.call_args_list
        bound_abstracts = [c.args[0] for c in calls]
        assert DomainEventPublisherProtocol in bound_abstracts

    @pytest.mark.asyncio
    async def test_register_binds_command_bus(self) -> None:
        """MemoryProvider registers CommandBusProtocol singleton."""
        from lexigram.contracts.events import CommandBusProtocol
        from lexigram.testing.memory.di.provider import MemoryProvider

        provider = MemoryProvider()
        container = MagicMock()
        await provider.register(container)

        calls = container.singleton.call_args_list
        bound_abstracts = [c.args[0] for c in calls]
        assert CommandBusProtocol in bound_abstracts

    @pytest.mark.asyncio
    async def test_register_binds_query_bus(self) -> None:
        """MemoryProvider registers QueryBusProtocol singleton."""
        from lexigram.contracts.events import QueryBusProtocol
        from lexigram.testing.memory.di.provider import MemoryProvider

        provider = MemoryProvider()
        container = MagicMock()
        await provider.register(container)

        calls = container.singleton.call_args_list
        bound_abstracts = [c.args[0] for c in calls]
        assert QueryBusProtocol in bound_abstracts


# ---------------------------------------------------------------------------
# Tests: Error propagation
# ---------------------------------------------------------------------------


class TestErrorPropagation:
    """Verify exceptions from handlers propagate to the caller."""

    @pytest.mark.asyncio
    async def test_handler_exception_propagates(self) -> None:
        """Exceptions from handlers are not silently swallowed."""

        async def bad_handler(event: OrderCreated) -> None:
            raise ValueError("handler failed")

        bus = InMemoryEventBus()
        bus.subscribe(OrderCreated, bad_handler)

        with pytest.raises(ValueError, match="handler failed"):
            await bus.publish(OrderCreated(order_id="err"))

    @pytest.mark.asyncio
    async def test_middleware_exception_propagates(self) -> None:
        """Exceptions from middleware propagate to the caller."""

        async def bad_mw(event: Any, next_handler: Any) -> None:
            raise RuntimeError("middleware exploded")

        bus = InMemoryEventBus()
        bus.add_middleware(bad_mw)
        bus.subscribe(OrderCreated, lambda e: None)

        with pytest.raises(RuntimeError, match="middleware exploded"):
            await bus.publish(OrderCreated(order_id="err"))
