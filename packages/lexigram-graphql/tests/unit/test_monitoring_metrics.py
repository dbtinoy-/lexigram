from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from lexigram.graphql.monitoring.metrics import (
    GraphQLMetrics,
    MetricsCollectorProtocol,
    MetricsExtension,
    QueryStats,
)


class TestQueryStats:
    def test_defaults(self) -> None:
        stats = QueryStats()
        assert stats.operation_name is None
        assert stats.operation_type == "query"
        assert stats.success is True
        assert stats.error_count == 0
        assert stats.duration_ms == 0.0

    def test_with_values(self) -> None:
        stats = QueryStats(
            operation_name="GetUser",
            operation_type="query",
            duration_ms=42.5,
            success=True,
            error_count=0,
        )
        assert stats.operation_name == "GetUser"
        assert stats.duration_ms == 42.5


class TestGraphQLMetrics:
    def test_defaults(self) -> None:
        m = GraphQLMetrics()
        assert m.total_requests == 0
        assert m.successful_requests == 0
        assert m.failed_requests == 0
        assert m.total_duration_ms == 0.0

    def test_record_request_success(self) -> None:
        m = GraphQLMetrics()
        stats = QueryStats(operation_name="Q", operation_type="query", duration_ms=10.0, success=True)
        m.record_request(stats)
        assert m.total_requests == 1
        assert m.successful_requests == 1
        assert m.total_duration_ms == 10.0

    def test_record_request_failure(self) -> None:
        m = GraphQLMetrics()
        stats = QueryStats(operation_name="Q", operation_type="mutation", duration_ms=5.0, success=False)
        m.record_request(stats)
        assert m.total_requests == 1
        assert m.failed_requests == 1
        assert m.operations_by_type == {"mutation": 1}

    def test_record_request_updates_average(self) -> None:
        m = GraphQLMetrics()
        m.record_request(QueryStats(duration_ms=10.0, success=True))
        m.record_request(QueryStats(duration_ms=20.0, success=True))
        assert m.avg_duration_ms == 15.0

    def test_record_request_without_name(self) -> None:
        m = GraphQLMetrics()
        m.record_request(QueryStats(operation_type="query", duration_ms=1.0, success=True))
        assert m.operations_by_name == {}

    def test_record_error(self) -> None:
        m = GraphQLMetrics()
        m.record_error("ValueError")
        m.record_error("ValueError")
        m.record_error("TypeError")
        assert m.errors_by_type == {"ValueError": 2, "TypeError": 1}

    def test_to_dict(self) -> None:
        m = GraphQLMetrics()
        m.record_request(QueryStats(duration_ms=100.0, success=True))
        d = m.to_dict()
        assert d["total_requests"] == 1
        assert d["success_rate"] == 100.0
        assert d["avg_duration_ms"] == 100.0

    def test_to_dict_no_requests(self) -> None:
        m = GraphQLMetrics()
        d = m.to_dict()
        assert d["total_requests"] == 0
        assert d["success_rate"] == 0.0


class TestMetricsCollectorProtocol:
    def test_record(self) -> None:
        collector = MetricsCollectorProtocol(max_history=10)
        stats = QueryStats(operation_name="GetUser", duration_ms=25.0, success=True)
        collector.record(stats)
        metrics = collector.get_metrics()
        assert metrics.total_requests == 1

    def test_record_with_recorder(self) -> None:
        recorder = MagicMock()
        collector = MetricsCollectorProtocol(max_history=10, recorder=recorder)
        stats = QueryStats(operation_name="GetUser", operation_type="query", duration_ms=25.0, success=True)
        collector.record(stats)
        recorder.gauge.assert_called_once()
        recorder.increment.assert_called()

    def test_record_failure_with_recorder(self) -> None:
        recorder = MagicMock()
        collector = MetricsCollectorProtocol(max_history=10, recorder=recorder)
        stats = QueryStats(operation_name="GetUser", duration_ms=25.0, success=False)
        collector.record(stats)
        # Should increment failed counter too
        assert recorder.increment.call_count >= 2

    def test_record_error(self) -> None:
        collector = MetricsCollectorProtocol()
        collector.record_error(ValueError("test"))
        metrics = collector.get_metrics()
        assert metrics.errors_by_type == {"ValueError": 1}

    def test_get_recent_stats(self) -> None:
        collector = MetricsCollectorProtocol(max_history=100)
        collector.record(QueryStats(operation_name="Q1", duration_ms=1.0, success=True))
        collector.record(QueryStats(operation_name="Q2", duration_ms=2.0, success=True))
        recent = collector.get_recent_stats(limit=1)
        assert len(recent) == 1
        assert recent[0].operation_name == "Q2"

    def test_get_recent_stats_all(self) -> None:
        collector = MetricsCollectorProtocol(max_history=100)
        collector.record(QueryStats(operation_name="Q1", duration_ms=1.0, success=True))
        recent = collector.get_recent_stats(limit=100)
        assert len(recent) == 1

    def test_reset(self) -> None:
        collector = MetricsCollectorProtocol()
        collector.record(QueryStats(duration_ms=1.0, success=True))
        collector.reset()
        metrics = collector.get_metrics()
        assert metrics.total_requests == 0

    @pytest.mark.asyncio
    async def test_close(self) -> None:
        collector = MetricsCollectorProtocol()
        collector.record(QueryStats(duration_ms=1.0, success=True))
        await collector.close()
        metrics = collector.get_metrics()
        assert metrics.total_requests == 0

    def test_history_bounded(self) -> None:
        collector = MetricsCollectorProtocol(max_history=3)
        for i in range(5):
            collector.record(QueryStats(operation_name=f"Q{i}", duration_ms=float(i), success=True))
        recent = collector.get_recent_stats(limit=10)
        assert len(recent) == 3
        assert recent[0].operation_name == "Q2"


class TestMetricsExtension:
    @pytest.mark.asyncio
    async def test_on_operation_with_collector(self) -> None:
        collector = MetricsCollectorProtocol()
        ext = MetricsExtension(collector=collector)
        # Mock execution_context
        ctx = MagicMock()
        ctx.operation_name = "TestOp"
        ctx.graphql_document = None
        ctx.result = MagicMock()
        ctx.result.errors = None
        ext.execution_context = ctx

        async def fake_yield():
            yield

        gen = ext.on_operation()
        await gen.__anext__()
        # After yield, stats should be recorded
        try:
            await gen.__anext__()
        except StopAsyncIteration:
            pass
        metrics = collector.get_metrics()
        assert metrics.total_requests >= 1
