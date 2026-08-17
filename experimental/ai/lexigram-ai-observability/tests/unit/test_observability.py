"""Unit tests for lexigram.ai.observability — health monitor, metrics, and tracing."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any
from unittest.mock import MagicMock

import pytest

from lexigram.ai.observability.health import AIHealthMonitor
from lexigram.contracts import HealthCheckResult, HealthStatus


# ── AIHealthMonitor ──────────────────────────────────────────────────


class TestAIHealthMonitor:
    @pytest.fixture
    def monitor(self) -> AIHealthMonitor:
        return AIHealthMonitor()

    def test_creation(self, monitor: AIHealthMonitor) -> None:
        assert monitor is not None
        assert monitor._llm_checks == {}
        assert monitor._vector_checks == {}

    def test_add_llm_check(self, monitor: AIHealthMonitor) -> None:
        async def fake_check() -> HealthCheckResult:
            return HealthCheckResult(
                status=HealthStatus.HEALTHY, component="llm.openai"
            )
        monitor.add_llm_check("openai", fake_check)
        assert "openai" in monitor._llm_checks

    def test_add_vector_check(self, monitor: AIHealthMonitor) -> None:
        monitor.add_vector_check("pgvector", lambda: None)
        assert "pgvector" in monitor._vector_checks

    def test_add_cache_check(self, monitor: AIHealthMonitor) -> None:
        monitor.add_cache_check("redis", lambda: None)
        assert "redis" in monitor._cache_checks

    def test_add_embedding_check(self, monitor: AIHealthMonitor) -> None:
        monitor.add_embedding_check("ada-002", lambda: None)
        assert "ada-002" in monitor._embedding_checks

    @pytest.mark.asyncio
    async def test_check_llm_unknown_provider(self, monitor: AIHealthMonitor) -> None:
        result = await monitor.check_llm("nonexistent")
        assert result.status == HealthStatus.UNKNOWN
        assert "No health check configured" in result.message

    @pytest.mark.asyncio
    async def test_check_llm_healthy(self, monitor: AIHealthMonitor) -> None:
        expected = HealthCheckResult(status=HealthStatus.HEALTHY, component="llm.openai")
        async def healthy() -> HealthCheckResult:
            return expected
        monitor.add_llm_check("openai", healthy)
        result = await monitor.check_llm("openai")
        assert result.status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_check_llm_exception(self, monitor: AIHealthMonitor) -> None:
        async def broken() -> HealthCheckResult:
            raise ConnectionError("timeout")
        monitor.add_llm_check("broken", broken)
        result = await monitor.check_llm("broken")
        assert result.status == HealthStatus.UNHEALTHY
        assert "timeout" in result.message

    @pytest.mark.asyncio
    async def test_check_vector_unknown(self, monitor: AIHealthMonitor) -> None:
        result = await monitor.check_vector("nonexistent")
        assert result.status == HealthStatus.UNKNOWN

    @pytest.mark.asyncio
    async def test_check_vector_healthy(self, monitor: AIHealthMonitor) -> None:
        expected = HealthCheckResult(
            status=HealthStatus.HEALTHY, component="vector.pgvector"
        )
        async def healthy() -> HealthCheckResult:
            return expected
        monitor.add_vector_check("pgvector", healthy)
        result = await monitor.check_vector("pgvector")
        assert result.status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_check_cache_exception(self, monitor: AIHealthMonitor) -> None:
        async def broken() -> HealthCheckResult:
            raise RuntimeError("connection refused")
        monitor.add_cache_check("redis", broken)
        result = await monitor.check_cache("redis")
        assert result.status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_check_all_empty(self, monitor: AIHealthMonitor) -> None:
        results = await monitor.check_all()
        assert results == {}

    @pytest.mark.asyncio
    async def test_check_all_multiple(self, monitor: AIHealthMonitor) -> None:
        async def healthy_llm() -> HealthCheckResult:
            return HealthCheckResult(status=HealthStatus.HEALTHY, component="llm.openai")
        async def healthy_vec() -> HealthCheckResult:
            return HealthCheckResult(status=HealthStatus.HEALTHY, component="vector.pg")
        monitor.add_llm_check("openai", healthy_llm)
        monitor.add_vector_check("pg", healthy_vec)
        results = await monitor.check_all()
        assert len(results) == 2
        assert all(r.status == HealthStatus.HEALTHY for r in results.values())

    @pytest.mark.asyncio
    async def test_is_ready_all_healthy(self, monitor: AIHealthMonitor) -> None:
        async def healthy() -> HealthCheckResult:
            return HealthCheckResult(status=HealthStatus.HEALTHY, component="test")
        monitor.add_llm_check("test", healthy)
        assert await monitor.is_ready() is True

    @pytest.mark.asyncio
    async def test_is_ready_unhealthy(self, monitor: AIHealthMonitor) -> None:
        async def unhealthy() -> HealthCheckResult:
            return HealthCheckResult(status=HealthStatus.UNHEALTHY, component="test")
        monitor.add_llm_check("test", unhealthy)
        assert await monitor.is_ready() is False

    @pytest.mark.asyncio
    async def test_is_live_no_checks(self, monitor: AIHealthMonitor) -> None:
        assert await monitor.is_live() is True

    @pytest.mark.asyncio
    async def test_is_live_one_healthy(self, monitor: AIHealthMonitor) -> None:
        async def healthy() -> HealthCheckResult:
            return HealthCheckResult(status=HealthStatus.HEALTHY, component="test")
        async def unhealthy() -> HealthCheckResult:
            return HealthCheckResult(status=HealthStatus.UNHEALTHY, component="bad")
        monitor.add_llm_check("good", healthy)
        monitor.add_llm_check("bad", unhealthy)
        assert await monitor.is_live() is True


# ── AIMetrics ────────────────────────────────────────────────────────


class TestAIMetrics:
    def _make_collector_mock(self) -> MagicMock:
        """Build a mock MetricsCollectorProtocol."""
        mock = MagicMock()
        mock.create_counter.return_value = MagicMock()
        mock.create_gauge.return_value = MagicMock()
        mock.create_histogram.return_value = MagicMock()
        return mock

    def test_creation_with_collector(self) -> None:
        from lexigram.ai.observability.metrics import AIMetrics
        collector = self._make_collector_mock()
        metrics = AIMetrics(collector=collector)
        assert metrics.llm_requests_total is not None
        assert metrics.rag_queries_total is not None

    def test_creation_without_collector_raises(self) -> None:
        from lexigram.ai.observability.metrics import AIMetrics
        with pytest.raises(ValueError, match="No metrics collector"):
            AIMetrics(collector=None)

    def test_get_collector(self) -> None:
        from lexigram.ai.observability.metrics import AIMetrics
        collector = self._make_collector_mock()
        metrics = AIMetrics(collector=collector)
        assert metrics.get_collector() is collector

    def test_metrics_instruments_created(self) -> None:
        from lexigram.ai.observability.metrics import AIMetrics
        collector = self._make_collector_mock()
        AIMetrics(collector=collector)
        assert collector.create_counter.call_count >= 10
        assert collector.create_histogram.call_count >= 5
        assert collector.create_gauge.call_count >= 5


# ── AITracer ─────────────────────────────────────────────────────────


class _FakeSpan:
    """Minimal span stub for tracer tests."""
    def __init__(self) -> None:
        self.attributes: dict[str, Any] = {}
        self.events: list[tuple[str, dict]] = []

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def add_event(self, name: str, attrs: dict | None = None) -> None:
        self.events.append((name, attrs or {}))


class TestAITracer:
    @pytest.fixture
    def tracer(self) -> Any:
        from lexigram.ai.observability.tracing import AITracer
        mock_tracer = MagicMock()
        fake_span = _FakeSpan()

        @contextmanager
        def fake_start_span(name: str, attributes: dict | None = None):
            yield fake_span

        mock_tracer.start_span = fake_start_span
        mock_tracer.get_current_span.return_value = fake_span
        return AITracer(tracer=mock_tracer), fake_span

    def test_trace_llm_call(self, tracer: tuple) -> None:
        ai_tracer, span = tracer
        with ai_tracer.trace_llm_call("openai", "gpt-4") as s:
            assert s is span

    def test_trace_vector_operation(self, tracer: tuple) -> None:
        ai_tracer, span = tracer
        with ai_tracer.trace_vector_operation("search", "pgvector", "docs") as s:
            assert s is span

    def test_trace_embedding_operation(self, tracer: tuple) -> None:
        ai_tracer, span = tracer
        with ai_tracer.trace_embedding_operation("ada-002", batch_size=10) as s:
            assert s is span

    def test_trace_rag_stage(self, tracer: tuple) -> None:
        ai_tracer, span = tracer
        with ai_tracer.trace_rag_stage("retrieval", "default") as s:
            assert s is span

    def test_trace_rag_query(self, tracer: tuple) -> None:
        ai_tracer, span = tracer
        with ai_tracer.trace_rag_query("What is Python?") as s:
            assert s is span

    def test_trace_operation(self, tracer: tuple) -> None:
        ai_tracer, span = tracer
        with ai_tracer.trace_operation("custom_op", key="val") as s:
            assert s is span

    def test_get_current_span(self, tracer: tuple) -> None:
        ai_tracer, span = tracer
        assert ai_tracer.get_current_span() is span
