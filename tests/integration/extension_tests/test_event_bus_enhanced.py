"""Tests for enhanced InMemoryEventBus with handler priority and error isolation."""

from __future__ import annotations

import pytest

from lexigram.contracts.domain.events import DomainEvent
from lexigram.testing.memory.event_bus import InMemoryEventBus


class SampleEvent(DomainEvent):
    """Test event for bus tests."""
    value: str = "test"


class TestEventBusPriority:
    """Test handler priority ordering in InMemoryEventBus."""

    @pytest.mark.asyncio
    async def test_handlers_execute_in_priority_order(self) -> None:
        """Handlers with lower priority values should execute first."""
        bus = InMemoryEventBus()
        execution_order: list[str] = []

        async def handler_a(event: DomainEvent) -> None:
            execution_order.append("a")

        async def handler_b(event: DomainEvent) -> None:
            execution_order.append("b")

        async def handler_c(event: DomainEvent) -> None:
            execution_order.append("c")

        bus.subscribe(SampleEvent, handler_c, priority=10)
        bus.subscribe(SampleEvent, handler_a, priority=1)
        bus.subscribe(SampleEvent, handler_b, priority=5)

        await bus.publish(SampleEvent(value="test"))
        assert execution_order == ["a", "b", "c"]

    @pytest.mark.asyncio
    async def test_default_priority_is_zero(self) -> None:
        """Handlers without explicit priority should default to 0."""
        bus = InMemoryEventBus()
        execution_order: list[str] = []

        async def handler_default(event: DomainEvent) -> None:
            execution_order.append("default")

        async def handler_high(event: DomainEvent) -> None:
            execution_order.append("high")

        bus.subscribe(SampleEvent, handler_high, priority=10)
        bus.subscribe(SampleEvent, handler_default)

        await bus.publish(SampleEvent(value="test"))
        assert execution_order == ["default", "high"]

    @pytest.mark.asyncio
    async def test_same_priority_preserves_insertion_order(self) -> None:
        """Handlers with equal priority should execute in registration order."""
        bus = InMemoryEventBus()
        execution_order: list[str] = []

        async def handler_first(event: DomainEvent) -> None:
            execution_order.append("first")

        async def handler_second(event: DomainEvent) -> None:
            execution_order.append("second")

        bus.subscribe(SampleEvent, handler_first, priority=0)
        bus.subscribe(SampleEvent, handler_second, priority=0)

        await bus.publish(SampleEvent(value="test"))
        assert execution_order == ["first", "second"]


class TestEventBusErrorHandling:
    """Test error isolation and on_handler_error callback."""

    @pytest.mark.asyncio
    async def test_error_handler_called_on_exception(self) -> None:
        """on_handler_error callback should receive event, handler, and exception."""
        error_log: list[tuple] = []

        def on_error(event: DomainEvent, handler: object, exc: Exception) -> None:
            error_log.append((event, handler, exc))

        bus = InMemoryEventBus(on_handler_error=on_error)

        async def failing_handler(event: DomainEvent) -> None:
            raise ValueError("boom")

        bus.subscribe(SampleEvent, failing_handler)
        event = SampleEvent(value="test")
        await bus.publish(event)

        assert len(error_log) == 1
        assert error_log[0][0] is event
        assert error_log[0][1] is failing_handler
        assert isinstance(error_log[0][2], ValueError)

    @pytest.mark.asyncio
    async def test_handler_isolation_continues_after_error(self) -> None:
        """When on_handler_error is set, remaining handlers should execute after a failure."""
        results: list[str] = []

        def on_error(event: DomainEvent, handler: object, exc: Exception) -> None:
            results.append("error_caught")

        bus = InMemoryEventBus(on_handler_error=on_error)

        async def good_handler_1(event: DomainEvent) -> None:
            results.append("handler_1")

        async def bad_handler(event: DomainEvent) -> None:
            raise RuntimeError("fail")

        async def good_handler_2(event: DomainEvent) -> None:
            results.append("handler_2")

        bus.subscribe(SampleEvent, good_handler_1, priority=0)
        bus.subscribe(SampleEvent, bad_handler, priority=1)
        bus.subscribe(SampleEvent, good_handler_2, priority=2)

        await bus.publish(SampleEvent(value="test"))
        assert results == ["handler_1", "error_caught", "handler_2"]

    @pytest.mark.asyncio
    async def test_error_propagates_without_handler(self) -> None:
        """Without on_handler_error, exceptions should propagate normally."""
        bus = InMemoryEventBus()

        async def failing_handler(event: DomainEvent) -> None:
            raise ValueError("no handler set")

        bus.subscribe(SampleEvent, failing_handler)

        with pytest.raises(ValueError, match="no handler set"):
            await bus.publish(SampleEvent(value="test"))

    @pytest.mark.asyncio
    async def test_unsubscribe_with_priority(self) -> None:
        """Unsubscribe should work correctly with priority-based handlers."""
        bus = InMemoryEventBus()
        called = False

        async def handler(event: DomainEvent) -> None:
            nonlocal called
            called = True

        bus.subscribe(SampleEvent, handler, priority=5)
        bus.unsubscribe(SampleEvent, handler)
        await bus.publish(SampleEvent(value="test"))
        assert not called
