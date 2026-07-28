"""Unit tests for database monitoring components"""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

try:
    import pytest_asyncio
except ImportError:
    pytest_asyncio = None  # type: ignore[assignment]
from lexigram.sql.monitoring.database_monitor import (
    ConnectionPoolMonitor,
    DatabaseHealthChecker,
    DatabaseMonitor,
    QueryMonitor,
    TransactionMonitor,
)
from lexigram.sql.monitoring.metrics import (
    HealthStatus,
    InMemoryDbMetricsCollector,
    QueryMetrics,
    TransactionMetrics,
)


@pytest.fixture(autouse=True)
def mock_db_logger():
    """Patch the db.monitor logger to use a standard library logger so caplog works."""
    with patch("lexigram.sql.monitoring.database_monitor.logger") as mock_log:
        yield mock_log


class TestQueryMonitor:
    """Test QueryMonitor functionality"""

    @pytest.fixture if pytest_asyncio is None else pytest_asyncio.fixture
    async def collector(self):
        """Create a test metrics collector"""
        return InMemoryDbMetricsCollector()

    @pytest.fixture if pytest_asyncio is None else pytest_asyncio.fixture
    async def monitor(self, collector):
        """Create a QueryMonitor instance with a small slow threshold for fast tests"""
        return QueryMonitor(collector, slow_query_threshold=0.01)

    @pytest.mark.asyncio
    async def test_init(self, collector):
        """Test QueryMonitor initialization"""
        monitor = QueryMonitor(collector, slow_query_threshold=0.05)
        assert monitor.collector == collector
        assert monitor.slow_query_threshold == 0.05

    @pytest.mark.asyncio
    async def test_monitor_query_success(self, monitor, collector):
        """Test successful query monitoring"""
        query = "SELECT * FROM users"

        async with monitor.monitor_query(query, parameters=[1], connection_id="conn1"):
            # Simulate query execution
            await asyncio.sleep(0.01)

        # Check that metrics were recorded
        assert len(collector.query_metrics) == 1
        metric = collector.query_metrics[0]
        assert metric.query == query
        assert metric.parameters == [1]
        assert metric.success is True
        assert metric.error_message is None
        assert metric.connection_id == "conn1"
        assert metric.execution_time >= 0.01

    @pytest.mark.asyncio
    async def test_monitor_query_failure(self, monitor, collector):
        """Test failed query monitoring"""
        query = "SELECT * FROM invalid_table"

        with pytest.raises(ValueError, match="Table does not exist"):
            async with monitor.monitor_query(query):
                raise ValueError("Table does not exist")

        # Check that metrics were recorded
        assert len(collector.query_metrics) == 1
        metric = collector.query_metrics[0]
        assert metric.query == query
        assert metric.success is False
        assert metric.error_message == "Table does not exist"

    @pytest.mark.asyncio
    async def test_monitor_query_slow_query_logging(
        self, monitor, collector, caplog, mock_db_logger
    ):
        """Test slow query logging"""

        caplog.set_level("WARNING")
        query = "SELECT * FROM large_table"

        async with monitor.monitor_query(query):
            await asyncio.sleep(0.02)  # Exceed threshold (0.01)

        # Check call instead of caplog
        assert mock_db_logger.warning.called
        args, _ = mock_db_logger.warning.call_args
        assert "SLOW QUERY" in args[0]
        assert query == args[2]

    @pytest.mark.asyncio
    async def test_get_stats(self, monitor, collector):
        """Test getting query statistics"""
        # Add some test metrics
        await collector.record_query_metrics(
            QueryMetrics(
                query="SELECT 1",
                parameters=None,
                execution_time=0.1,
                timestamp=datetime.now(UTC),
                success=True,
            ),
        )

        stats = await monitor.get_stats()
        assert stats["total_queries"] == 1
        assert stats["successful_queries"] == 1
        assert stats["failed_queries"] == 0


class TestTransactionMonitor:
    """Test TransactionMonitor functionality"""

    @pytest.fixture if pytest_asyncio is None else pytest_asyncio.fixture
    async def collector(self):
        """Create a test metrics collector"""
        return InMemoryDbMetricsCollector()

    @pytest.fixture if pytest_asyncio is None else pytest_asyncio.fixture
    async def monitor(self, collector):
        """Create a TransactionMonitor instance"""
        return TransactionMonitor(collector)

    @pytest.mark.asyncio
    async def test_init(self, collector):
        """Test TransactionMonitor initialization"""
        monitor = TransactionMonitor(collector)
        assert monitor.collector == collector

    @pytest.mark.asyncio
    async def test_monitor_transaction_success(self, monitor, collector):
        """Test successful transaction monitoring"""
        transaction_id = "tx123"

        async with monitor.monitor_transaction(transaction_id):
            await asyncio.sleep(0.01)

        # Check that metrics were recorded
        assert len(collector.transaction_metrics) == 1
        metric = collector.transaction_metrics[0]
        assert metric.transaction_id == transaction_id
        assert metric.success is True
        assert metric.operation == "commit"
        assert metric.deadlock_detected is False
        assert metric.duration >= 0.01

    @pytest.mark.asyncio
    async def test_monitor_transaction_failure(self, monitor, collector):
        """Test failed transaction monitoring"""
        transaction_id = "tx456"

        with pytest.raises(RuntimeError):
            async with monitor.monitor_transaction(transaction_id):
                raise RuntimeError("Transaction failed")

        # Check that metrics were recorded
        assert len(collector.transaction_metrics) == 1
        metric = collector.transaction_metrics[0]
        assert metric.transaction_id == transaction_id
        assert metric.success is False
        assert metric.operation == "rollback"
        assert "Transaction failed" in metric.error_message

    @pytest.mark.asyncio
    async def test_monitor_transaction_deadlock_detection(self, monitor, collector):
        """Test deadlock detection in transaction failures"""
        transaction_id = "tx789"

        with pytest.raises(RuntimeError):
            async with monitor.monitor_transaction(transaction_id):
                raise RuntimeError("Deadlock detected")

        # Check deadlock detection
        assert len(collector.transaction_metrics) == 1
        metric = collector.transaction_metrics[0]
        assert metric.deadlock_detected is True

    @pytest.mark.asyncio
    async def test_get_stats(self, monitor, collector):
        """Test getting transaction statistics"""
        # Add some test metrics
        await collector.record_transaction_metrics(
            TransactionMetrics(
                transaction_id="tx1",
                start_time=datetime.now(UTC),
                end_time=datetime.now(UTC),
                duration=0.1,
                operation="commit",
                success=True,
                deadlock_detected=False,
            ),
        )

        stats = await monitor.get_stats()
        assert stats["total_transactions"] == 1
        assert stats["successful_transactions"] == 1
        assert stats["commit_ratio"] == 1.0


class TestHealthChecker:
    """Test DatabaseHealthChecker functionality"""

    @pytest.fixture if pytest_asyncio is None else pytest_asyncio.fixture
    async def collector(self):
        """Create a test metrics collector"""
        return InMemoryDbMetricsCollector()

    @pytest.fixture if pytest_asyncio is None else pytest_asyncio.fixture
    async def checker(self, collector):
        """Create a DatabaseHealthChecker instance"""
        return DatabaseHealthChecker(collector)

    @pytest.mark.asyncio
    async def test_init(self, collector):
        """Test DatabaseHealthChecker initialization"""
        checker = DatabaseHealthChecker(collector)
        assert checker.collector == collector

    @pytest.mark.asyncio
    async def test_check_database_health_success(self, checker):
        """Test successful database health check"""
        # Mock a successful database connection
        with patch("sqlalchemy.create_engine") as mock_engine:
            mock_conn = MagicMock()
            mock_result = MagicMock()
            mock_result.fetchone.return_value = [1]
            mock_conn.execute.return_value = mock_result
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=None)

            mock_engine.return_value.connect.return_value.__enter__ = MagicMock(
                return_value=mock_conn,
            )
            mock_engine.return_value.connect.return_value.__exit__ = MagicMock(
                return_value=None,
            )
            mock_engine.return_value.dispose = MagicMock()

            result = await checker.check_database_health("sqlite:///test.db")

            assert result.status == "healthy"
            assert "successful" in result.message
            assert result.component == "database"

    @pytest.mark.asyncio
    async def test_check_database_health_failure(self, checker):
        """Test failed database health check"""
        with patch("sqlalchemy.create_engine") as mock_engine:
            mock_engine.side_effect = RuntimeError("Connection failed")

            result = await checker.check_database_health("invalid://connection")

            assert result.status == "critical"
            assert "failed" in result.message

    @pytest.mark.asyncio
    async def test_check_connection_pool_health(self, checker):
        """Test connection pool health check"""
        # Mock a connection pool
        pool = MagicMock()
        pool._active_connections = 8
        pool._total_connections = 10

        result = await checker.check_connection_pool_health(pool)

        assert result.status == "healthy"
        assert "healthy" in result.message
        assert result.details["utilization"] == 0.8

    @pytest.mark.asyncio
    async def test_check_connection_pool_health_overutilized(self, checker):
        """Test overutilized connection pool health check"""
        pool = MagicMock()
        pool._active_connections = 9
        pool._total_connections = 10

        result = await checker.check_connection_pool_health(pool)

        assert result.status == "warning"
        assert "highly utilized" in result.message

    @pytest.mark.asyncio
    async def test_check_database_health_timeout(self, checker):
        """Test database health check timeout"""
        with patch("sqlalchemy.create_engine") as mock_engine:
            # Mock timeout
            mock_engine.side_effect = TimeoutError()

            result = await checker.check_database_health(
                "timeout://connection",
                timeout=0.1,
            )

            assert result.status == "critical"
            assert "timeout" in result.message

    @pytest.mark.asyncio
    async def test_check_database_health_query_failure(self, checker):
        """Test database health check where query returns unexpected result"""
        with patch("sqlalchemy.create_engine") as mock_engine:
            mock_conn = MagicMock()
            mock_result = MagicMock()
            mock_result.fetchone.return_value = [0]  # Not 1
            mock_conn.execute.return_value = mock_result
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=None)

            mock_engine.return_value.connect.return_value.__enter__ = MagicMock(
                return_value=mock_conn,
            )
            mock_engine.return_value.connect.return_value.__exit__ = MagicMock(
                return_value=None,
            )
            mock_engine.return_value.dispose = MagicMock()

            result = await checker.check_database_health("sqlite:///test.db")

            assert result.status == "critical"
            assert "failed" in result.message

    @pytest.mark.asyncio
    async def test_check_database_health_with_sqlite_file(self, checker, tmp_path):
        """Integration-like unit test: real SQLite file should return healthy"""
        # Use an in-memory SQLite DB for a deterministic unit check
        conn_str = "sqlite:///:memory:"

        result = await checker.check_database_health(conn_str, timeout=1.0)
        assert result.status == "healthy", (
            f"status={result.status}, message={result.message}"
        )
        assert "successful" in result.message

    @pytest.mark.asyncio
    async def test_check_connection_pool_health_critical_utilization(self, checker):
        """Test connection pool health with critical utilization"""
        pool = MagicMock()
        pool._active_connections = 96
        pool._total_connections = 100

        result = await checker.check_connection_pool_health(pool)

        assert result.status == "critical"
        assert "critically overutilized" in result.message

    @pytest.mark.asyncio
    async def test_check_connection_pool_health_exception(self, checker):
        """Test connection pool health check with exception"""
        pool = MagicMock()
        pool._active_connections = MagicMock(
            side_effect=AttributeError("No such attribute"),
        )

        result = await checker.check_connection_pool_health(pool)

        assert result.status == "critical"
        assert "failed" in result.message
        assert "error" in result.details

    @pytest.mark.asyncio
    async def test_check_performance_health_critical_query_time(
        self,
        checker,
        collector,
    ):
        """Test performance health with critical query time"""
        # Add slow query metrics
        await collector.record_query_metrics(
            QueryMetrics(
                query="SELECT * FROM slow_table",
                parameters=None,
                execution_time=3.0,  # Above critical threshold (2.0)
                timestamp=datetime.now(UTC),
                success=True,
            ),
        )

        results = await checker.check_performance_health()

        query_check = next(
            (r for r in results if r.component == "query_performance"),
            None,
        )
        assert query_check is not None
        assert query_check.status == "critical"
        assert "critically high" in query_check.message

    @pytest.mark.asyncio
    async def test_check_performance_health_warning_query_time(
        self,
        checker,
        collector,
    ):
        """Test performance health with warning query time"""
        # Add moderately slow query
        await collector.record_query_metrics(
            QueryMetrics(
                query="SELECT * FROM medium_table",
                parameters=None,
                execution_time=0.8,  # Above warning threshold (0.5) but below critical (2.0)
                timestamp=datetime.now(UTC),
                success=True,
            ),
        )

        results = await checker.check_performance_health()

        query_check = next(
            (r for r in results if r.component == "query_performance"),
            None,
        )
        assert query_check is not None
        assert query_check.status == "warning"
        assert "elevated" in query_check.message

    @pytest.mark.asyncio
    async def test_check_performance_health_critical_commit_ratio(
        self,
        checker,
        collector,
    ):
        """Test performance health with critical commit ratio"""
        # Add failed transactions
        await collector.record_transaction_metrics(
            TransactionMetrics(
                transaction_id="tx1",
                start_time=datetime.now(UTC),
                end_time=datetime.now(UTC),
                duration=0.1,
                operation="rollback",
                success=False,
                deadlock_detected=False,
            ),
        )

        results = await checker.check_performance_health()

        tx_check = next(
            (r for r in results if r.component == "transaction_performance"),
            None,
        )
        assert tx_check is not None
        assert tx_check.status == "critical"
        assert "critically low" in tx_check.message

    @pytest.mark.asyncio
    async def test_check_performance_health_warning_commit_ratio(
        self,
        checker,
        collector,
    ):
        """Test performance health with warning commit ratio"""
        # Add transactions to get commit ratio between warning and critical thresholds
        # Need commit_ratio >= 0.7 and < 0.85 for warning
        # With 7 commits and 3 rollbacks = 10 total, ratio = 0.7
        for i in range(7):
            await collector.record_transaction_metrics(
                TransactionMetrics(
                    transaction_id=f"tx_commit_{i}",
                    start_time=datetime.now(UTC),
                    end_time=datetime.now(UTC),
                    duration=0.1,
                    operation="commit",
                    success=True,
                    deadlock_detected=False,
                ),
            )
        for i in range(3):
            await collector.record_transaction_metrics(
                TransactionMetrics(
                    transaction_id=f"tx_rollback_{i}",
                    start_time=datetime.now(UTC),
                    end_time=datetime.now(UTC),
                    duration=0.1,
                    operation="rollback",
                    success=False,
                    deadlock_detected=False,
                ),
            )

        results = await checker.check_performance_health()

        tx_check = next(
            (r for r in results if r.component == "transaction_performance"),
            None,
        )
        assert tx_check is not None
        assert tx_check.status == "warning"
        assert "low" in tx_check.message


class TestConnectionPoolMonitor:
    """Test ConnectionPoolMonitor functionality"""

    @pytest.fixture if pytest_asyncio is None else pytest_asyncio.fixture
    async def collector(self):
        """Create a test metrics collector"""
        return InMemoryDbMetricsCollector()

    @pytest.fixture if pytest_asyncio is None else pytest_asyncio.fixture
    async def monitor(self, collector):
        """Create a ConnectionPoolMonitor instance"""
        return ConnectionPoolMonitor(collector)

    @pytest.mark.asyncio
    async def test_init(self, collector):
        """Test ConnectionPoolMonitor initialization"""
        monitor = ConnectionPoolMonitor(collector)
        assert monitor.collector == collector
        assert monitor.monitoring_task is None
        assert monitor.pool is None

    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, monitor):
        """Test starting and stopping pool monitoring"""
        pool = MagicMock()
        pool._active_connections = 5
        pool._total_connections = 10

        await monitor.start_monitoring(pool)
        assert monitor.pool == pool
        assert monitor.monitoring_task is not None

        await monitor.stop_monitoring()
        assert monitor.monitoring_task is None

    @pytest.mark.asyncio
    async def test_collect_pool_metrics(self, monitor, collector):
        """Test collecting pool metrics"""
        pool = MagicMock()
        pool._active_connections = 3
        pool._total_connections = 10

        monitor.pool = pool
        await monitor._collect_pool_metrics()

        # Check that metrics were recorded
        assert len(collector.connection_metrics) == 1
        metric = collector.connection_metrics[0]
        assert metric.active_connections == 3
        assert metric.total_connections == 10
        assert metric.utilization == 0.3

    @pytest.mark.asyncio
    async def test_probe_pool_executes_select_one(self, monitor):
        """Probe executes a lightweight health query through the provider."""
        provider = MagicMock()
        scoped_context = MagicMock()
        scoped_context.__aenter__ = AsyncMock(return_value=None)
        scoped_context.__aexit__ = AsyncMock(return_value=False)
        connection = MagicMock()
        connection.execute = AsyncMock()

        provider.scoped_context.return_value = scoped_context
        provider.get_scoped_connection = AsyncMock(return_value=connection)
        provider.evict_dead_connections = AsyncMock()
        monitor._provider = provider

        await monitor._probe_pool()

        connection.execute.assert_awaited_once_with("SELECT 1")
        provider.evict_dead_connections.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_probe_pool_failure_requests_eviction(self, monitor):
        """Probe failure triggers best-effort dead-connection eviction."""
        provider = MagicMock()
        scoped_context = MagicMock()
        scoped_context.__aenter__ = AsyncMock(return_value=None)
        scoped_context.__aexit__ = AsyncMock(return_value=False)

        provider.scoped_context.return_value = scoped_context
        provider.get_scoped_connection = AsyncMock(
            side_effect=ConnectionError("dead pool")
        )
        provider.evict_dead_connections = AsyncMock()
        monitor._provider = provider

        await monitor._probe_pool()

        provider.evict_dead_connections.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_probe_pool_without_eviction_support_does_not_raise(self, monitor):
        """Probe failure is tolerated when provider lacks eviction support."""

        class ProviderWithoutEviction:
            def __init__(self) -> None:
                scoped_context = MagicMock()
                scoped_context.__aenter__ = AsyncMock(return_value=None)
                scoped_context.__aexit__ = AsyncMock(return_value=False)
                self._scoped_context = scoped_context

            def scoped_context(self) -> MagicMock:
                return self._scoped_context

            async def get_scoped_connection(self) -> None:
                raise ConnectionError("dead pool")

        monitor._provider = ProviderWithoutEviction()

        await monitor._probe_pool()

    @pytest.mark.asyncio
    async def test_probe_pool_failure_logs_eviction_count(
        self, monitor, mock_db_logger
    ):
        """Probe failure logs the number of connections remaining after eviction."""
        provider = MagicMock()
        scoped_context = MagicMock()
        scoped_context.__aenter__ = AsyncMock(return_value=None)
        scoped_context.__aexit__ = AsyncMock(return_value=False)

        provider.scoped_context.return_value = scoped_context
        provider.get_scoped_connection = AsyncMock(
            side_effect=ConnectionError("dead pool")
        )
        # Provider supports eviction and returns count of remaining connections
        provider.evict_dead_connections = AsyncMock(return_value=3)
        monitor._provider = provider

        await monitor._probe_pool()

        provider.evict_dead_connections.assert_awaited_once()
        # Should log the eviction result with the count of remaining connections
        # Check that info or warning was called with a message about remaining connections
        all_calls = [str(c) for c in mock_db_logger.info.call_args_list] + [
            str(c) for c in mock_db_logger.warning.call_args_list
        ]
        # The implementation should log something like "3 connections remaining"
        # or "evicted ... 3 remaining" after calling evict_dead_connections()
        found_eviction_log = any(
            ("remaining" in call.lower() and "3" in call)
            or ("evict" in call.lower() and "3" in call)
            for call in all_calls
        )
        assert found_eviction_log, (
            f"Expected log message about eviction with count 3, but got: {all_calls}"
        )

    @pytest.mark.asyncio
    async def test_collect_pool_metrics_exception(
        self, monitor, collector, caplog, mock_db_logger
    ):
        """Test pool metrics collection with exception"""

        caplog.set_level("ERROR")
        pool = MagicMock()
        # Use PropertyMock to trigger side_effect on attribute ACCESS
        type(pool)._active_connections = PropertyMock(
            side_effect=RuntimeError("Pool error")
        )
        monitor.pool = pool

        await monitor._collect_pool_metrics()

        # Check call instead of caplog
        assert mock_db_logger.exception.called
        args, _ = mock_db_logger.exception.call_args
        assert "Error collecting pool metrics" in args[0]

    @pytest.mark.asyncio
    async def test_monitor_pool_exception_handling(
        self, monitor, collector, caplog, mock_db_logger
    ):
        """Test pool monitoring exception handling"""

        caplog.set_level("ERROR")
        pool = MagicMock()
        pool._active_connections = 5
        pool._total_connections = 10
        monitor.pool = pool

        # Mock _collect_pool_metrics to raise an exception
        async def failing_collect():
            raise RuntimeError("Monitor error")

        monitor._collect_pool_metrics = failing_collect

        # Start monitoring and let it run briefly
        await monitor.start_monitoring(pool)
        await asyncio.sleep(0.02)  # Let the monitoring task run
        await monitor.stop_monitoring()

        # Check call instead of caplog
        assert mock_db_logger.exception.called
        args, _ = mock_db_logger.exception.call_args
        assert "Error monitoring connection pool" in args[0]


class TestDatabaseMonitor:
    """Test DatabaseMonitor functionality"""

    @pytest.fixture if pytest_asyncio is None else pytest_asyncio.fixture
    async def monitor(self):
        """Create a DatabaseMonitor instance"""
        return DatabaseMonitor()

    @pytest.mark.asyncio
    async def test_init(self):
        """Test DatabaseMonitor initialization"""
        monitor = DatabaseMonitor()
        assert isinstance(monitor.collector, InMemoryDbMetricsCollector)
        assert isinstance(monitor.query_monitor, QueryMonitor)
        assert isinstance(monitor.transaction_monitor, TransactionMonitor)
        assert isinstance(monitor.health_checker, DatabaseHealthChecker)
        assert isinstance(monitor.pool_monitor, ConnectionPoolMonitor)

    @pytest.mark.asyncio
    async def test_init_with_custom_collector(self):
        """Test DatabaseMonitor with custom collector"""
        collector = InMemoryDbMetricsCollector()
        monitor = DatabaseMonitor(collector)
        assert monitor.collector == collector

    @pytest.mark.asyncio
    async def test_get_monitors(self, monitor):
        """Test getting monitor instances"""
        assert isinstance(monitor.get_query_monitor(), QueryMonitor)
        assert isinstance(monitor.get_transaction_monitor(), TransactionMonitor)
        assert isinstance(monitor.get_health_checker(), DatabaseHealthChecker)

    @pytest.mark.asyncio
    async def test_get_stats(self, monitor):
        """Test getting comprehensive statistics"""
        stats = await monitor.get_stats()
        assert "query_stats" in stats
        assert "connection_stats" in stats
        assert "transaction_stats" in stats
        assert "timestamp" in stats

    @pytest.mark.asyncio
    async def test_perform_health_check_with_pool(self, monitor):
        """Test performing health check with connection pool"""
        pool = MagicMock()
        pool._active_connections = 5
        pool._total_connections = 10

        with patch.object(
            monitor.health_checker,
            "check_database_health",
            new_callable=AsyncMock,
        ) as mock_db_check:
            mock_db_check.return_value = HealthStatus(
                component="database",
                status="healthy",
                message="OK",
                timestamp=datetime.now(UTC),
            )

            result = await monitor.perform_health_check("sqlite:///test.db", pool=pool)

            assert "checks" in result
            assert len(result["checks"]) >= 2  # Database + pool checks

    @pytest.mark.asyncio
    async def test_perform_health_check_critical_status(self, monitor):
        """Test health check aggregation with critical status"""
        with (
            patch.object(
                monitor.health_checker,
                "check_database_health",
                new_callable=AsyncMock,
            ) as mock_db_check,
            patch.object(
                monitor.health_checker,
                "check_performance_health",
                new_callable=AsyncMock,
            ) as mock_perf_check,
        ):
            mock_db_check.return_value = HealthStatus(
                component="database",
                status="critical",
                message="DB down",
                timestamp=datetime.now(UTC),
            )
            mock_perf_check.return_value = []

            result = await monitor.perform_health_check("sqlite:///test.db")

            assert result["overall_status"] == "critical"

    @pytest.mark.asyncio
    async def test_perform_health_check_warning_status(self, monitor):
        """Test health check aggregation with warning status"""
        with (
            patch.object(
                monitor.health_checker,
                "check_database_health",
                new_callable=AsyncMock,
            ) as mock_db_check,
            patch.object(
                monitor.health_checker,
                "check_performance_health",
                new_callable=AsyncMock,
            ) as mock_perf_check,
        ):
            mock_db_check.return_value = HealthStatus(
                component="database",
                status="warning",
                message="DB slow",
                timestamp=datetime.now(UTC),
            )
            mock_perf_check.return_value = []

            result = await monitor.perform_health_check("sqlite:///test.db")

            assert result["overall_status"] == "warning"

    @pytest.mark.asyncio
    async def test_perform_health_check_healthy_status(self, monitor):
        """Test health check aggregation with healthy status"""
        with (
            patch.object(
                monitor.health_checker,
                "check_database_health",
                new_callable=AsyncMock,
            ) as mock_db_check,
            patch.object(
                monitor.health_checker,
                "check_performance_health",
                new_callable=AsyncMock,
            ) as mock_perf_check,
        ):
            mock_db_check.return_value = HealthStatus(
                component="database",
                status="healthy",
                message="OK",
                timestamp=datetime.now(UTC),
            )
            mock_perf_check.return_value = []

            result = await monitor.perform_health_check("sqlite:///test.db")

            assert result["overall_status"] == "healthy"

    @pytest.mark.asyncio
    async def test_perform_health_check_unknown_status(self, monitor):
        """Test health check aggregation with unknown status"""
        with (
            patch.object(
                monitor.health_checker,
                "check_database_health",
                new_callable=AsyncMock,
            ) as mock_db_check,
            patch.object(
                monitor.health_checker,
                "check_performance_health",
                new_callable=AsyncMock,
            ) as mock_perf_check,
        ):
            mock_db_check.return_value = HealthStatus(
                component="database",
                status="unknown",
                message="Unknown",
                timestamp=datetime.now(UTC),
            )
            mock_perf_check.return_value = []

            result = await monitor.perform_health_check("sqlite:///test.db")

            assert result["overall_status"] == "unknown"

    @pytest.mark.asyncio
    async def test_start_stop_pool_monitoring(self, monitor):
        """Test pool monitoring lifecycle"""
        pool = MagicMock()

        await monitor.start_pool_monitoring(pool)
        assert monitor.pool_monitor.pool == pool

        await monitor.stop_pool_monitoring()
        assert monitor.pool_monitor.monitoring_task is None

    @pytest.mark.asyncio
    async def test_start_pool_monitoring_uses_pool_as_provider_when_supported(
        self,
        monitor,
    ):
        """Provider-capable pools are threaded through for active probing."""
        pool = MagicMock()
        pool.scoped_context = MagicMock()

        await monitor.start_pool_monitoring(pool)

        assert monitor.pool_monitor.pool == pool
        assert monitor.pool_monitor._provider == pool

        await monitor.stop_pool_monitoring()

    @pytest.mark.asyncio
    async def test_start_pool_monitoring_allows_explicit_provider(
        self,
        monitor,
    ):
        """Explicit provider overrides pool inference."""
        pool = MagicMock()
        provider = MagicMock()

        await monitor.start_pool_monitoring(pool, provider=provider)

        assert monitor.pool_monitor.pool == pool
        assert monitor.pool_monitor._provider == provider

        await monitor.stop_pool_monitoring()
