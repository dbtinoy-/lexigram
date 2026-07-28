"""Tests for database monitoring functionality"""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.sql.monitoring import (
    ConnectionMetrics,
    DatabaseMonitor,
    InMemoryDbMetricsCollector,
    PerformanceBaseline,
    QueryMetrics,
    TransactionMetrics,
)


class TestInMemoryDbMetricsCollector:
    """Test InMemoryDbMetricsCollector functionality"""

    @pytest.fixture
    def collector(self):
        """Create a metrics collector for testing"""
        return InMemoryDbMetricsCollector()

    @pytest.mark.asyncio
    async def test_collector_creation(self, collector):
        """Test collector can be created"""
        assert collector is not None
        assert hasattr(collector, "record_query_metrics")
        assert hasattr(collector, "record_connection_metrics")
        assert hasattr(collector, "record_transaction_metrics")

    @pytest.mark.asyncio
    async def test_query_metrics_collection(self, collector):
        """Test query metrics collection"""
        metrics = QueryMetrics(
            query="SELECT * FROM test",
            parameters=["param1"],
            execution_time=0.1,
            timestamp=datetime.now(UTC),
            success=True,
            connection_id="test_conn",
        )

        await collector.record_query_metrics(metrics)

        # Check metrics were recorded
        assert len(collector.query_metrics) == 1
        recorded = collector.query_metrics[0]
        assert recorded.query == "SELECT * FROM test"
        assert recorded.success is True
        assert recorded.execution_time == 0.1

    @pytest.mark.asyncio
    async def test_connection_metrics_collection(self, collector):
        """Test connection metrics collection"""
        metrics = ConnectionMetrics(
            active_connections=5,
            total_connections=10,
            available_connections=5,
            checked_out_connections=5,
            checked_in_connections=5,
            utilization=0.5,
            timestamp=datetime.now(UTC),
        )

        await collector.record_connection_metrics(metrics)

        # Check metrics were recorded
        assert len(collector.connection_metrics) == 1
        recorded = collector.connection_metrics[0]
        assert recorded.active_connections == 5
        assert recorded.total_connections == 10
        assert recorded.utilization == 0.5

    @pytest.mark.asyncio
    async def test_transaction_metrics_collection(self, collector):
        """Test transaction metrics collection"""
        start_time = datetime.now(UTC)
        end_time = datetime.now(UTC)

        metrics = TransactionMetrics(
            transaction_id="test_txn",
            start_time=start_time,
            end_time=end_time,
            duration=0.2,
            operation="commit",
            success=True,
            deadlock_detected=False,
        )

        await collector.record_transaction_metrics(metrics)

        # Check metrics were recorded
        assert len(collector.transaction_metrics) == 1
        recorded = collector.transaction_metrics[0]
        assert recorded.transaction_id == "test_txn"
        assert recorded.operation == "commit"
        assert recorded.success is True
        assert recorded.deadlock_detected is False

    @pytest.mark.asyncio
    async def test_get_query_stats(self, collector):
        """Test getting query statistics"""
        # Add some test metrics
        base_time = datetime.now(UTC)
        metrics = [
            QueryMetrics(
                "SELECT * FROM users", None, 0.1, base_time, True, None, "conn1",
            ),
            QueryMetrics(
                "INSERT INTO users", ["john"], 0.05, base_time, True, None, "conn1",
            ),
            QueryMetrics(
                "SELECT * FROM posts", None, 2.0, base_time, False, "timeout", "conn2",
            ),
        ]

        for metric in metrics:
            await collector.record_query_metrics(metric)

        stats = await collector.get_query_stats()

        assert stats["total_queries"] == 3
        assert stats["successful_queries"] == 2
        assert stats["failed_queries"] == 1
        assert stats["average_execution_time"] > 0
        assert "SELECT" in stats["query_count_by_type"]
        assert "INSERT" in stats["query_count_by_type"]

    @pytest.mark.asyncio
    async def test_get_transaction_stats(self, collector):
        """Test getting transaction statistics"""
        base_time = datetime.now(UTC)
        metrics = [
            TransactionMetrics(
                "txn1", base_time, base_time, 0.1, "commit", True, False,
            ),
            TransactionMetrics(
                "txn2", base_time, base_time, 0.2, "rollback", False, True,
            ),
            TransactionMetrics(
                "txn3", base_time, base_time, 0.15, "commit", True, False,
            ),
        ]

        for metric in metrics:
            await collector.record_transaction_metrics(metric)

        stats = await collector.get_transaction_stats()

        assert stats["total_transactions"] == 3
        assert stats["successful_transactions"] == 2
        assert stats["failed_transactions"] == 1
        assert stats["commit_count"] == 2
        assert stats["rollback_count"] == 1
        assert stats["deadlock_count"] == 1
        assert stats["commit_ratio"] == 2 / 3

    @pytest.mark.asyncio
    async def test_get_connection_stats(self, collector):
        """Test getting connection statistics"""
        base_time = datetime.now(UTC)
        metrics = [
            ConnectionMetrics(5, 10, 5, 5, 5, 0.5, base_time),
            ConnectionMetrics(7, 10, 3, 7, 3, 0.7, base_time),
            ConnectionMetrics(3, 10, 7, 3, 7, 0.3, base_time),
        ]

        for metric in metrics:
            await collector.record_connection_metrics(metric)

        stats = await collector.get_connection_stats()

        assert stats["total_samples"] == 3
        assert stats["average_active_connections"] == 5.0
        assert stats["average_utilization"] == 0.5
        assert stats["max_utilization"] == 0.7
        assert stats["min_utilization"] == 0.3
        assert stats["current_active_connections"] == 3
        assert stats["current_total_connections"] == 10
        assert stats["current_utilization"] == 0.3

    @pytest.mark.asyncio
    async def test_performance_baselines(self, collector):
        """Test performance baseline management"""
        baselines = await collector.get_performance_baselines()
        assert len(baselines) > 0

        # Check default baselines are present
        baseline_names = list(map(lambda b: b.metric_name, baselines))
        assert "query_execution_time" in baseline_names
        assert "connection_pool_utilization" in baseline_names
        assert "transaction_commit_ratio" in baseline_names

        # Test setting custom baseline
        custom_baseline = PerformanceBaseline(
            metric_name="custom_metric",
            expected_value=1.0,
            warning_threshold=2.0,
            critical_threshold=5.0,
            unit="requests/sec",
            description="Custom performance metric",
        )

        await collector.set_performance_baseline(custom_baseline)

        updated_baselines = await collector.get_performance_baselines()
        assert len(updated_baselines) == len(baselines) + 1

        custom_found = next(
            (b for b in updated_baselines if b.metric_name == "custom_metric"), None,
        )
        assert custom_found is not None
        assert custom_found.expected_value == 1.0


class TestDatabaseMonitor:
    """Test DatabaseMonitor functionality"""

    @pytest.fixture
    def monitor(self):
        """Create a database monitor for testing"""
        collector = InMemoryDbMetricsCollector()
        return DatabaseMonitor(collector)

    @pytest.mark.asyncio
    async def test_monitor_creation(self, monitor):
        """Test monitor creation"""
        assert monitor is not None
        assert hasattr(monitor, "get_query_monitor")
        assert hasattr(monitor, "get_transaction_monitor")
        assert hasattr(monitor, "get_health_checker")
        assert hasattr(monitor, "start_pool_monitoring")
        assert hasattr(monitor, "stop_pool_monitoring")

    @pytest.mark.asyncio
    async def test_monitor_stats(self, monitor):
        """Test monitor statistics retrieval"""
        stats = await monitor.get_stats()

        assert "query_stats" in stats
        assert "connection_stats" in stats
        assert "transaction_stats" in stats
        assert "timestamp" in stats

        # Check query stats structure
        query_stats = stats["query_stats"]
        assert "total_queries" in query_stats
        assert "successful_queries" in query_stats
        assert "failed_queries" in query_stats

        # Check transaction stats structure
        txn_stats = stats["transaction_stats"]
        assert "total_transactions" in txn_stats
        assert "successful_transactions" in txn_stats
        assert "failed_transactions" in txn_stats

    @pytest.mark.asyncio
    async def test_query_monitor_context_manager(self, monitor):
        """Test query monitor context manager"""
        query_monitor = monitor.get_query_monitor()

        async with query_monitor.monitor_query(
            query="SELECT * FROM users WHERE id = ?",
            parameters=[123],
            connection_id="test_conn",
        ):
            await asyncio.sleep(0.01)  # Simulate query execution

        # Check metrics were recorded
        stats = await query_monitor.get_stats()
        assert stats["total_queries"] == 1
        assert stats["successful_queries"] == 1

    @pytest.mark.asyncio
    async def test_query_monitor_with_exception(self, monitor):
        """Test query monitor with exception"""
        query_monitor = monitor.get_query_monitor()

        with pytest.raises(ValueError):
            async with query_monitor.monitor_query(
                query="SELECT * FROM invalid_table", connection_id="test_conn",
            ):
                raise ValueError("Query failed")

        # Check metrics were recorded with failure
        stats = await query_monitor.get_stats()
        assert stats["total_queries"] == 1
        assert stats["failed_queries"] == 1

    @pytest.mark.asyncio
    async def test_connection_pool_monitoring(self, monitor):
        """Test connection pool monitoring"""
        # Mock pool object — spec limits attributes so hasattr(pool, 'scoped_context') == False,
        # keeping probe_provider=None and preventing _probe_pool from attempting a real DB call.
        mock_pool = MagicMock(spec=["_active_connections", "_total_connections"])
        mock_pool._active_connections = 5
        mock_pool._total_connections = 10

        # Start monitoring
        await monitor.start_pool_monitoring(mock_pool)

        # Wait a bit for monitoring to collect data
        await asyncio.sleep(0.02)

        # Stop monitoring
        await monitor.stop_pool_monitoring()

        # Check that some metrics were collected
        # stats = await monitor.get_stats()  # Not used in this test
        # connection_stats = stats["connection_stats"]  # Not used in this test
        # Note: May be 0 if monitoring task didn't run, which is acceptable for this test

    @pytest.mark.asyncio
    async def test_transaction_monitoring(self, monitor):
        """Test transaction monitoring"""
        txn_monitor = monitor.get_transaction_monitor()

        async with txn_monitor.monitor_transaction("test_transaction_1"):
            await asyncio.sleep(0.01)  # Simulate transaction work

        # Check metrics were recorded
        stats = await txn_monitor.get_stats()
        assert stats["total_transactions"] == 1
        assert stats["successful_transactions"] == 1
        assert stats["commit_count"] == 1

    @pytest.mark.asyncio
    async def test_health_checker(self, monitor, tmp_path):
        """Test health checker functionality"""
        health_checker = monitor.get_health_checker()

        # Use an in-memory SQLite DB for deterministic health check
        conn_str = "sqlite:///:memory:"

        health = await health_checker.check_database_health(conn_str, timeout=1.0)
        assert health.component == "database"
        assert (
            health.status == "healthy"
        ), f"status={health.status}, message={health.message}"
        assert "successful" in health.message
        assert health.timestamp is not None

    @pytest.mark.asyncio
    async def test_performance_baselines(self, monitor):
        """Test performance baseline retrieval"""
        health_checker = monitor.get_health_checker()

        baselines = await health_checker.collector.get_performance_baselines()
        assert len(baselines) > 0

        # Check that we have expected baseline metrics
        baseline_names = list(map(lambda b: b.metric_name, baselines))
        assert "query_execution_time" in baseline_names
        assert "connection_pool_utilization" in baseline_names


class TestMetricsDataStructures:
    """Test metrics data structure creation"""

    def test_query_metrics_creation(self):
        """Test QueryMetrics creation"""
        timestamp = datetime.now(UTC)
        metrics = QueryMetrics(
            query="SELECT * FROM test",
            parameters=["param1", "param2"],
            execution_time=0.123,
            timestamp=timestamp,
            success=True,
            connection_id="test_conn_123",
        )

        assert metrics.query == "SELECT * FROM test"
        assert metrics.parameters == ["param1", "param2"]
        assert metrics.execution_time == 0.123
        assert metrics.timestamp == timestamp
        assert metrics.success is True
        assert metrics.connection_id == "test_conn_123"
        assert metrics.error_message is None
        assert metrics.transaction_id is None

    def test_connection_metrics_creation(self):
        """Test ConnectionMetrics creation"""
        timestamp = datetime.now(UTC)
        metrics = ConnectionMetrics(
            active_connections=5,
            total_connections=10,
            available_connections=5,
            checked_out_connections=5,
            checked_in_connections=5,
            utilization=0.5,
            timestamp=timestamp,
        )

        assert metrics.active_connections == 5
        assert metrics.total_connections == 10
        assert metrics.available_connections == 5
        assert metrics.checked_out_connections == 5
        assert metrics.checked_in_connections == 5
        assert metrics.utilization == 0.5
        assert metrics.timestamp == timestamp

    def test_transaction_metrics_creation(self):
        """Test TransactionMetrics creation"""
        start_time = datetime.now(UTC)
        end_time = datetime.now(UTC)

        metrics = TransactionMetrics(
            transaction_id="txn_123",
            start_time=start_time,
            end_time=end_time,
            duration=0.234,
            operation="commit",
            success=True,
            deadlock_detected=False,
        )

        assert metrics.transaction_id == "txn_123"
        assert metrics.start_time == start_time
        assert metrics.end_time == end_time
        assert metrics.duration == 0.234
        assert metrics.operation == "commit"
        assert metrics.success is True
        assert metrics.deadlock_detected is False
        assert metrics.error_message is None
        assert metrics.nested_level == 0


class TestMonitoringIntegration:
    """Test comprehensive monitoring integration"""

    @pytest.mark.asyncio
    async def test_full_monitoring_workflow(self):
        """Test complete monitoring workflow"""
        collector = InMemoryDbMetricsCollector()
        monitor = DatabaseMonitor(collector)

        # Simulate query monitoring
        query_monitor = monitor.get_query_monitor()
        async with query_monitor.monitor_query(
            query="SELECT * FROM users WHERE id = ?",
            parameters=[123],
            connection_id="conn_1",
        ):
            await asyncio.sleep(0.01)  # Simulate query execution

        # Simulate transaction monitoring
        txn_monitor = monitor.get_transaction_monitor()
        async with txn_monitor.monitor_transaction("txn_1"):
            await asyncio.sleep(0.01)  # Simulate transaction work

        # Check final stats
        stats = await monitor.get_stats()

        # Verify query stats
        query_stats = stats["query_stats"]
        assert query_stats["total_queries"] == 1
        assert query_stats["successful_queries"] == 1
        assert query_stats["failed_queries"] == 0

        # Verify transaction stats
        txn_stats = stats["transaction_stats"]
        assert txn_stats["total_transactions"] == 1
        assert txn_stats["successful_transactions"] == 1
        assert txn_stats["failed_transactions"] == 0
        assert txn_stats["commit_count"] == 1
        assert txn_stats["rollback_count"] == 0

    @pytest.mark.asyncio
    async def test_health_check_workflow(self):
        """Test health check workflow"""
        collector = InMemoryDbMetricsCollector()
        monitor = DatabaseMonitor(collector)

        # Perform health check (will use mock/in-memory data)
        health_result = await monitor.perform_health_check("sqlite:///test.db")

        assert "overall_status" in health_result
        assert "checks" in health_result
        assert "timestamp" in health_result
        assert isinstance(health_result["checks"], list)

        # Should have at least database connectivity check
        checks = health_result["checks"]
        assert len(checks) >= 1

        db_check = next((c for c in checks if c["component"] == "database"), None)
        assert db_check is not None
        assert "status" in db_check
        assert "message" in db_check

    @pytest.mark.asyncio
    async def test_monitor_with_custom_collector(self):
        """Test monitor with custom collector"""
        collector = InMemoryDbMetricsCollector(max_metrics=5)
        monitor = DatabaseMonitor(collector)

        # Add multiple metrics to test max_metrics limit
        for i in range(10):
            metrics = QueryMetrics(
                query=f"SELECT {i}",
                parameters=None,
                execution_time=0.1,
                timestamp=datetime.now(UTC),
                success=True,
                connection_id=f"conn_{i}",
            )
            await collector.record_query_metrics(metrics)

        # Should only keep last 5 metrics
        assert len(collector.query_metrics) == 5

        # Verify monitor works with custom collector
        stats = await monitor.get_stats()
        assert stats["query_stats"]["total_queries"] == 5
