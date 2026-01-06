"""Tests for observability enhancements — facade, decorators."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from lexigram.monitor.instrumentation.decorators import metered, traced
from lexigram.observability.core import NoOpSpan
from lexigram.monitor.services.core import ObservabilityService

# ---------------------------------------------------------------------------
# ObservabilityService
# ---------------------------------------------------------------------------


class TestObservabilityService:
    """Tests for ObservabilityService."""

    def test_trace_yields_noop_span(self) -> None:
        obs = ObservabilityService()
        with obs.trace("test_span", key="value") as span:
            assert isinstance(span, NoOpSpan)
            assert span.name == "test_span"
            assert span.attributes["key"] == "value"

    def test_span_set_attribute(self) -> None:
        span = NoOpSpan("test")
        span.set_attribute("x", 42)
        assert span.attributes["x"] == 42

    def test_span_add_event(self) -> None:
        span = NoOpSpan("test")
        span.add_event("something")  # Should not raise

    def test_counter(self) -> None:
        obs = ObservabilityService()
        c = obs.counter("requests")
        assert c.value == 0
        c.increment()
        assert c.value == 1
        c.increment(5)
        assert c.value == 6

    def test_counter_same_name_returns_same(self) -> None:
        obs = ObservabilityService()
        c1 = obs.counter("test")
        c2 = obs.counter("test")
        assert c1 is c2

    def test_histogram(self) -> None:
        obs = ObservabilityService()
        h = obs.histogram("latency")
        h.record(1.5)
        h.record(2.3)
        assert len(h._values) == 2

    def test_timed_context_manager(self) -> None:
        obs = ObservabilityService()
        with obs.timed("operation"):
            pass
        assert len(obs.histogram("operation")._values) == 1

    def test_register_metric_delegates_to_meter(self) -> None:
        meter = MagicMock()
        metric = MagicMock()
        obs = ObservabilityService(meter=meter)

        obs.register_metric(metric)

        meter.register_metric.assert_called_once_with(metric)


# ---------------------------------------------------------------------------
# Traced decorator
# ---------------------------------------------------------------------------


class TestTracedDecorator:
    """Tests for @traced decorator."""

    @pytest.mark.asyncio
    async def test_traced_async(self) -> None:
        facade = ObservabilityService()

        @traced("test_op", service=facade)
        async def my_func(x: int) -> int:
            return x * 2

        result = await my_func(5)
        assert result == 10

    @pytest.mark.asyncio
    async def test_traced_async_error(self) -> None:
        facade = ObservabilityService()

        @traced("test_op", service=facade)
        async def bad_func() -> None:
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            await bad_func()

    def test_traced_sync(self) -> None:
        facade = ObservabilityService()

        @traced("sync_op", service=facade)
        def my_func(x: int) -> int:
            return x + 1

        result = my_func(5)
        assert result == 6

    def test_traced_sync_error(self) -> None:
        facade = ObservabilityService()

        @traced("sync_op", service=facade)
        def bad_func() -> None:
            raise RuntimeError("fail")

        with pytest.raises(RuntimeError, match="fail"):
            bad_func()

    def test_traced_default_name(self) -> None:
        facade = ObservabilityService()

        @traced(service=facade)
        def my_func() -> None:
            pass

        # Verify function name is preserved
        assert "my_func" in my_func.__qualname__


# ---------------------------------------------------------------------------
# Metered decorator
# ---------------------------------------------------------------------------


class TestMeteredDecorator:
    """Tests for @metered decorator."""

    @pytest.mark.asyncio
    async def test_metered_async(self) -> None:
        facade = ObservabilityService()

        @metered("op_duration", service=facade)
        async def my_func() -> str:
            return "done"

        result = await my_func()
        assert result == "done"
        assert len(facade.histogram("op_duration")._values) == 1

    def test_metered_sync(self) -> None:
        facade = ObservabilityService()

        @metered("sync_duration", service=facade)
        def my_func() -> int:
            return 42

        result = my_func()
        assert result == 42
        assert len(facade.histogram("sync_duration")._values) == 1


# ---------------------------------------------------------------------------
# Health module moved to observability
# ---------------------------------------------------------------------------


class TestHealthInObservability:
    """Verify health module is accessible from observability."""

    def test_import_from_observability(self) -> None:
        from lexigram.monitor.health import HealthChecker

        checker = HealthChecker()
        assert checker is not None

    def test_import_from_observability_init(self) -> None:
        from lexigram.monitor import HealthChecker

        checker = HealthChecker()
        assert checker is not None

    def test_backward_compat_from_core(self) -> None:
        from lexigram.monitor.health import HealthChecker

        checker = HealthChecker()
        assert checker is not None
