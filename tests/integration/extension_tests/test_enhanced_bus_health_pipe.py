"""Tests for enhanced EventBusProtocol, HealthChecker, and PipeProtocol features."""

from __future__ import annotations

import pytest

from lexigram.contracts.core import HealthCheckResult, HealthStatus
from lexigram.contracts.domain.events import DomainEvent
from lexigram.testing.memory.event_bus import InMemoryEventBus
from lexigram.monitor.health import HealthChecker, health_checker
from lexigram.workflow.core.pipe import TransformPipe

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


class OrderCreated(DomainEvent):
    order_id: str = ""


class OrderShipped(DomainEvent):
    order_id: str = ""


# ===========================================================================
# Enhanced EventBusProtocol
# ===========================================================================


class TestEventBusSubscriberCount:
    """Tests for subscriber_count property."""

    def test_empty(self) -> None:
        assert InMemoryEventBus().subscriber_count == 0

    def test_counts_all_subscriptions(self) -> None:
        bus = InMemoryEventBus()

        async def h1(e: DomainEvent) -> None:
            pass

        async def h2(e: DomainEvent) -> None:
            pass

        bus.subscribe(OrderCreated, h1)
        bus.subscribe(OrderCreated, h2)
        bus.subscribe(OrderShipped, h1)
        assert bus.subscriber_count == 3

    def test_after_unsubscribe(self) -> None:
        bus = InMemoryEventBus()

        async def h1(e: DomainEvent) -> None:
            pass

        bus.subscribe(OrderCreated, h1)
        bus.unsubscribe(OrderCreated, h1)
        assert bus.subscriber_count == 0


class TestEventBusSubscribedTypes:
    """Tests for subscribed_types property."""

    def test_empty(self) -> None:
        assert InMemoryEventBus().subscribed_types == set()

    def test_returns_types_with_handlers(self) -> None:
        bus = InMemoryEventBus()

        async def h(e: DomainEvent) -> None:
            pass

        bus.subscribe(OrderCreated, h)
        bus.subscribe(OrderShipped, h)
        assert bus.subscribed_types == {OrderCreated, OrderShipped}


class TestEventBusPublishMany:
    """Tests for publish_many method."""

    @pytest.mark.asyncio
    async def test_publishes_all_events(self) -> None:
        bus = InMemoryEventBus()
        received: list[str] = []

        async def handler(e: OrderCreated) -> None:
            received.append(e.order_id)

        bus.subscribe(OrderCreated, handler)
        await bus.publish_many(
            [
                OrderCreated(order_id="1"),
                OrderCreated(order_id="2"),
                OrderCreated(order_id="3"),
            ],
        )
        assert received == ["1", "2", "3"]

    @pytest.mark.asyncio
    async def test_empty_list_is_noop(self) -> None:
        bus = InMemoryEventBus()
        await bus.publish_many([])  # should not raise


class TestEventBusDeadLetterHandler:
    """Tests for dead_letter_handler callback."""

    @pytest.mark.asyncio
    async def test_fires_when_no_subscribers(self) -> None:
        dead: list[DomainEvent] = []
        bus = InMemoryEventBus(dead_letter_handler=dead.append)
        await bus.publish(OrderCreated(order_id="orphan"))
        assert len(dead) == 1
        assert dead[0].order_id == "orphan"

    @pytest.mark.asyncio
    async def test_not_fired_when_handler_exists(self) -> None:
        dead: list[DomainEvent] = []
        bus = InMemoryEventBus(dead_letter_handler=dead.append)

        async def h(e: DomainEvent) -> None:
            pass

        bus.subscribe(OrderCreated, h)
        await bus.publish(OrderCreated(order_id="handled"))
        assert len(dead) == 0

    @pytest.mark.asyncio
    async def test_async_dead_letter_handler(self) -> None:
        dead: list[DomainEvent] = []

        async def async_dlh(e: DomainEvent) -> None:
            dead.append(e)

        bus = InMemoryEventBus(dead_letter_handler=async_dlh)
        await bus.publish(OrderCreated(order_id="x"))
        assert len(dead) == 1


class TestEventBusHandlerTimeout:
    """Tests for handler_timeout support."""

    @pytest.mark.asyncio
    async def test_timeout_triggers_error_handler(self) -> None:
        import asyncio

        errors: list[Exception] = []

        def on_error(event: DomainEvent, handler: object, exc: Exception) -> None:
            errors.append(exc)

        bus = InMemoryEventBus(on_handler_error=on_error, handler_timeout=0.01)

        async def slow(e: DomainEvent) -> None:
            await asyncio.sleep(1.0)

        bus.subscribe(OrderCreated, slow)
        await bus.publish(OrderCreated(order_id="slow"))
        assert len(errors) == 1
        assert isinstance(errors[0], asyncio.TimeoutError)


# ===========================================================================
# HealthChecker — Enhanced Features
# ===========================================================================


class TestHealthCheckerRemove:
    """Tests for remove method."""

    def test_remove_existing(self) -> None:
        hc = HealthChecker()
        hc.add("db", lambda: True)
        hc.remove("db")
        assert not hc.has("db")

    def test_remove_missing_raises(self) -> None:
        hc = HealthChecker()
        with pytest.raises(KeyError):
            hc.remove("nope")


class TestHealthCheckerHas:
    """Tests for has method."""

    def test_has_true(self) -> None:
        hc = HealthChecker()
        hc.add("db", lambda: True)
        assert hc.has("db") is True

    def test_has_false(self) -> None:
        hc = HealthChecker()
        assert hc.has("db") is False


class TestHealthCheckerCheckNames:
    """Tests for check_names property."""

    def test_empty(self) -> None:
        assert HealthChecker().check_names == []

    def test_sorted_order(self) -> None:
        hc = HealthChecker()
        hc.add("cache", lambda: True)
        hc.add("db", lambda: True)
        hc.add("api", lambda: True)
        assert hc.check_names == ["api", "cache", "db"]


class TestHealthCheckerAggregateStatus:
    """Tests for aggregate_status method."""

    def test_all_healthy(self) -> None:
        hc = HealthChecker()
        results = {
            "a": HealthCheckResult(component="a", status=HealthStatus.HEALTHY),
            "b": HealthCheckResult(component="b", status=HealthStatus.HEALTHY),
        }
        assert hc.aggregate_status(results) == HealthStatus.HEALTHY

    def test_one_unhealthy(self) -> None:
        hc = HealthChecker()
        results = {
            "a": HealthCheckResult(component="a", status=HealthStatus.HEALTHY),
            "b": HealthCheckResult(component="b", status=HealthStatus.UNHEALTHY),
        }
        assert hc.aggregate_status(results) == HealthStatus.UNHEALTHY

    def test_degraded(self) -> None:
        hc = HealthChecker()
        results = {
            "a": HealthCheckResult(component="a", status=HealthStatus.HEALTHY),
            "b": HealthCheckResult(component="b", status=HealthStatus.DEGRADED),
        }
        assert hc.aggregate_status(results) == HealthStatus.DEGRADED

    def test_empty_results(self) -> None:
        hc = HealthChecker()
        assert hc.aggregate_status({}) == HealthStatus.UNKNOWN


class TestHealthCheckerRunAllWithSummary:
    """Tests for run_all_with_summary method."""

    @pytest.mark.asyncio
    async def test_returns_tuple(self) -> None:
        hc = HealthChecker()
        hc.add("db", lambda: True)
        status, results = await hc.run_all_with_summary()
        assert status == HealthStatus.HEALTHY
        assert "db" in results

    @pytest.mark.asyncio
    async def test_unhealthy_summary(self) -> None:
        hc = HealthChecker()

        def failing() -> bool:
            raise RuntimeError("db down")

        hc.add("db", failing)
        status, results = await hc.run_all_with_summary()
        assert status == HealthStatus.UNHEALTHY
        assert results["db"].status == HealthStatus.UNHEALTHY


class TestHealthCheckerTimeout:
    """Tests for per-check timeout support."""

    @pytest.mark.asyncio
    async def test_timeout_marks_unhealthy(self) -> None:
        import asyncio

        async def slow() -> bool:
            await asyncio.sleep(2.0)
            return True

        hc = HealthChecker()
        hc.add("slow", slow, timeout=0.01)
        results = await hc.run_all()
        assert results["slow"].status == HealthStatus.UNHEALTHY
        assert "timed out" in results["slow"].message


class TestHealthCheckerDecorator:
    """Tests for @health_checker decorator."""

    def test_register_decorated(self) -> None:
        @health_checker("cache")
        def check_cache() -> bool:
            return True

        hc = HealthChecker()
        hc.register(check_cache)
        assert hc.has("cache")

    def test_register_undecorated_raises(self) -> None:
        hc = HealthChecker()
        with pytest.raises(ValueError, match="not decorated"):
            hc.register(lambda: True)


# ===========================================================================
# TransformPipe — Enhanced Features (tap, pipe_if, catch)
# ===========================================================================


class TestPipeTap:
    """Tests for the tap method (side-effect observation)."""

    @pytest.mark.asyncio
    async def test_tap_observes_value(self) -> None:
        observed: list[int] = []
        result = await TransformPipe().pipe(lambda x: x + 1).tap(observed.append).execute(5)
        assert result == 6
        assert observed == [6]

    @pytest.mark.asyncio
    async def test_tap_does_not_transform(self) -> None:
        result = await TransformPipe().tap(lambda x: x * 100).execute(42)
        assert result == 42

    @pytest.mark.asyncio
    async def test_async_tap(self) -> None:
        observed: list[int] = []

        async def log_value(v: int) -> None:
            observed.append(v)

        result = await TransformPipe().tap(log_value).execute(10)
        assert result == 10
        assert observed == [10]


class TestPipePipeIf:
    """Tests for the pipe_if method (conditional transformation)."""

    @pytest.mark.asyncio
    async def test_applies_when_predicate_true(self) -> None:
        result = await TransformPipe().pipe_if(lambda x: x > 0, lambda x: x * 2).execute(5)
        assert result == 10

    @pytest.mark.asyncio
    async def test_skips_when_predicate_false(self) -> None:
        result = await TransformPipe().pipe_if(lambda x: x > 100, lambda x: x * 2).execute(5)
        assert result == 5

    @pytest.mark.asyncio
    async def test_async_step_in_pipe_if(self) -> None:
        async def double(x: int) -> int:
            return x * 2

        result = await TransformPipe().pipe_if(lambda x: True, double).execute(7)
        assert result == 14


class TestPipeCatch:
    """Tests for the catch method (error recovery)."""

    @pytest.mark.asyncio
    async def test_recovers_on_error(self) -> None:
        def crash(x: int) -> int:
            raise ValueError("boom")

        result = await TransformPipe().pipe(crash).catch(lambda exc, val: -1).execute(5)
        assert result == -1

    @pytest.mark.asyncio
    async def test_no_catch_propagates(self) -> None:
        def crash(x: int) -> int:
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            await TransformPipe().pipe(crash).execute(5)

    @pytest.mark.asyncio
    async def test_catch_receives_last_value(self) -> None:
        captured: list = []

        def crash(x: int) -> int:
            raise ValueError("err")

        def handler(exc: Exception, val: int) -> int:
            captured.append((type(exc).__name__, val))
            return 0

        await TransformPipe().pipe(lambda x: x + 10).pipe(crash).catch(handler).execute(5)
        assert captured == [("ValueError", 15)]
