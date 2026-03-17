"""Tests for PostgreSQL database driver"""

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock, patch

import pytest

try:
    import asyncpg

    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False
    asyncpg = None  # type: ignore[assignment]

from lexigram.contracts.core import HealthStatus
from lexigram.sql.backends.postgres import (
    HAS_POSTGRES,
    PostgresConnection,
    PostgresConnectionPool,
    create_postgres_pool,
)
from lexigram.sql.exceptions import DatabaseConnectionError, QueryError


@pytest.mark.skipif(not HAS_POSTGRES, reason="asyncpg not available")
class TestPostgresDriver:
    """Test PostgreSQL driver functionality"""

    @pytest.fixture
    def mock_monitor(self):
        """Create a mock monitor"""
        monitor = Mock()
        query_monitor = Mock()

        # Create a mock for monitor_query that can track calls
        monitor_query_mock = Mock()

        @asynccontextmanager
        async def monitor_query(*args, **kwargs):
            yield Mock()

        # Make monitor_query both callable and have mock methods
        monitor_query_mock.side_effect = monitor_query
        query_monitor.monitor_query = monitor_query_mock
        monitor.get_query_monitor.return_value = query_monitor
        monitor.start_pool_monitoring = AsyncMock()
        monitor.stop_pool_monitoring = AsyncMock()
        monitor.get_stats = AsyncMock(return_value={})
        return monitor

    @pytest.mark.asyncio
    async def test_postgres_pool_creation(self):
        """Test PostgreSQL pool creation"""
        with patch("lexigram.sql.backends.postgres.asyncpg") as mock_asyncpg:
            mock_asyncpg.PostgresError = Exception
            mock_pool = AsyncMock()
            mock_asyncpg.create_pool = AsyncMock(return_value=mock_pool)

            pool = PostgresConnectionPool("postgresql://user:pass@localhost:5432/test")
            await pool.initialize()

            mock_asyncpg.create_pool.assert_called_once()
            call_args = mock_asyncpg.create_pool.call_args
            assert call_args[1]["min_size"] == 10
            assert call_args[1]["max_size"] == 20

    @pytest.mark.asyncio
    async def test_postgres_pool_initialization_success(self):
        """Test PostgreSQL pool initialization success"""
        with patch("lexigram.sql.backends.postgres.asyncpg") as mock_asyncpg:
            mock_asyncpg.PostgresError = Exception
            mock_pool = AsyncMock()
            mock_asyncpg.create_pool = AsyncMock(return_value=mock_pool)

            pool = PostgresConnectionPool("postgresql://user:pass@localhost:5432/test")
            await pool.initialize()

            assert pool._pool is not None
            assert pool._is_healthy is True
            assert pool._total_connections_created == 1

    @pytest.mark.asyncio
    async def test_postgres_pool_initialization_with_ssl(self):
        """Test PostgreSQL pool initialization with SSL"""
        with patch("lexigram.sql.backends.postgres.asyncpg") as mock_asyncpg:
            mock_asyncpg.PostgresError = Exception
            mock_pool = AsyncMock()
            mock_asyncpg.create_pool = AsyncMock(return_value=mock_pool)

            pool = PostgresConnectionPool(
                "postgresql://user:pass@localhost:5432/test",
                ssl={"verify_cert": False},
            )

            await pool.initialize()

            mock_asyncpg.create_pool.assert_called_once()
            call_args = mock_asyncpg.create_pool.call_args
            assert call_args[1]["ssl"] is not None

    @pytest.mark.asyncio
    async def test_postgres_pool_initialization_failure(self):
        """Test PostgreSQL pool initialization failure"""
        with patch("lexigram.sql.backends.postgres.asyncpg") as mock_asyncpg:
            mock_asyncpg.create_pool = AsyncMock(
                side_effect=Exception("Connection failed"),
            )

            # Create a custom retry config with proper exception types
            from lexigram.contracts.infra.resilience import RetryConfig

            retry_config = RetryConfig(
                max_attempts=3,
                base_delay=1.0,
                retry_on=(ConnectionError,),
            )

            pool = PostgresConnectionPool(
                "postgresql://user:pass@localhost:5432/test",
                retry_config=retry_config,
            )

            with pytest.raises(DatabaseConnectionError, match="Pool creation failed"):
                await pool.initialize()

            assert pool._pool is None
            assert pool._is_healthy is False
            assert pool._error_count == 1

    @pytest.mark.asyncio
    async def test_postgres_pool_double_initialization(self):
        """Test PostgreSQL pool double initialization"""
        with patch("lexigram.sql.backends.postgres.asyncpg") as mock_asyncpg:
            mock_asyncpg.PostgresError = Exception
            mock_pool = AsyncMock()
            mock_asyncpg.create_pool = AsyncMock(return_value=mock_pool)

            pool = PostgresConnectionPool("postgresql://user:pass@localhost:5432/test")
            await pool.initialize()
            await pool.initialize()  # Should not create pool again

            # Should only be called once
            mock_asyncpg.create_pool.assert_called_once()

    @pytest.mark.asyncio
    async def test_postgres_connection_creation(self):
        """Test PostgreSQL connection creation"""
        with patch("lexigram.sql.backends.postgres.asyncpg") as mock_asyncpg:
            mock_asyncpg.PostgresError = Exception
            mock_pool = AsyncMock()
            mock_conn = AsyncMock()

            # Mock pool.acquire() to return an async context manager
            @asynccontextmanager
            async def mock_acquire():
                yield mock_conn

            mock_pool.acquire = mock_acquire
            mock_asyncpg.create_pool = AsyncMock(return_value=mock_pool)

            pool = PostgresConnectionPool("postgresql://user:pass@localhost:5432/test")
            await pool.initialize()

            # Mock circuit breaker as async context manager
            mock_circuit_breaker = AsyncMock()

            @asynccontextmanager
            async def mock_protect():
                yield

            mock_circuit_breaker.protect = mock_protect
            mock_circuit_breaker.state = AsyncMock()
            mock_circuit_breaker.state.value = "closed"
            pool.circuit_breaker = mock_circuit_breaker

            async with pool.get_connection() as conn:
                assert isinstance(conn, PostgresConnection)
                assert conn._conn == mock_conn
                assert pool._connection_count == 1

    @pytest.mark.asyncio
    async def test_postgres_connection_execute_without_monitoring(self):
        """Test PostgreSQL connection execute without monitoring"""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="INSERT 1")

        conn = PostgresConnection(mock_conn)

        result = await conn.execute("INSERT INTO test VALUES ($1)", (1,))

        assert result == "INSERT 1"
        mock_conn.execute.assert_called_once_with("INSERT INTO test VALUES ($1)", 1)

    @pytest.mark.asyncio
    async def test_postgres_connection_execute_with_monitoring(self, mock_monitor):
        """Test PostgreSQL connection execute with monitoring"""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="INSERT 1")

        conn = PostgresConnection(mock_conn, mock_monitor)

        result = await conn.execute("INSERT INTO test VALUES ($1)", (1,))

        assert result == "INSERT 1"
        mock_monitor.get_query_monitor.assert_called_once()
        mock_monitor.get_query_monitor().monitor_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_postgres_connection_execute_error(self):
        """Test PostgreSQL connection execute error"""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(side_effect=asyncpg.PostgresError("Syntax error"))

        conn = PostgresConnection(mock_conn)

        with pytest.raises(QueryError) as exc_info:
            await conn.execute("INVALID SQL")

        error = exc_info.value
        assert "Query execution failed" in str(error)
        assert error.details["query"] == "INVALID SQL"
        assert "Syntax error" in error.details["error"]

    @pytest.mark.asyncio
    async def test_postgres_connection_execute_many(self):
        """Test PostgreSQL connection execute_many"""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value="INSERT 1")

        # Mock transaction as async context manager
        @asynccontextmanager
        async def mock_transaction():
            yield

        mock_conn.transaction = mock_transaction

        conn = PostgresConnection(mock_conn)

        params_list = [(1,), (2,), (3,)]
        await conn.execute_many("INSERT INTO test VALUES ($1)", params_list)

        # Verify executes were called
        assert mock_conn.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_get_stats_reports_monitoring_enabled(self, mock_monitor):
        """Pool.get_stats should report monitoring availability"""
        with patch("lexigram.sql.backends.postgres.HAS_MONITORING", True):
            pool = PostgresConnectionPool(
                "postgresql://user:pass@localhost:5432/test",
                monitor=mock_monitor,
            )
            stats = await pool.get_pool_stats()
            assert stats.get("monitoring_enabled") is True

    @pytest.mark.asyncio
    async def test_postgres_connection_execute_many_error(self):
        """Test PostgreSQL connection execute_many error"""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(
            side_effect=asyncpg.PostgresError("Constraint violation"),
        )

        # Mock transaction as async context manager
        @asynccontextmanager
        async def mock_transaction():
            yield

        mock_conn.transaction = mock_transaction

        conn = PostgresConnection(mock_conn)

        params_list = [(1,), (2,)]
        with pytest.raises(QueryError) as exc_info:
            await conn.execute_many("INSERT INTO test VALUES ($1)", params_list)

        error = exc_info.value
        assert "Batch execution failed" in str(error)
        assert error.details["query"] == "INSERT INTO test VALUES ($1)"
        assert "Constraint violation" in error.details["error"]

    @pytest.mark.asyncio
    async def test_postgres_connection_fetch_one_without_monitoring(self):
        """Test PostgreSQL connection fetch_one without monitoring"""
        mock_conn = AsyncMock()
        mock_record = Mock()
        mock_record.__getitem__ = Mock(
            side_effect=lambda k: {"id": 1, "name": "test"}[k],
        )
        mock_record.keys = Mock(return_value=["id", "name"])
        mock_conn.fetchrow = AsyncMock(return_value=mock_record)

        conn = PostgresConnection(mock_conn)

        result = await conn.fetch_one("SELECT * FROM test WHERE id = $1", (1,))

        assert result == {"id": 1, "name": "test"}
        mock_conn.fetchrow.assert_called_once_with(
            "SELECT * FROM test WHERE id = $1",
            1,
        )

    @pytest.mark.asyncio
    async def test_postgres_connection_fetch_one_with_monitoring(self, mock_monitor):
        """Test PostgreSQL connection fetch_one with monitoring"""
        mock_conn = AsyncMock()
        mock_record = Mock()
        mock_record.__getitem__ = Mock(
            side_effect=lambda k: {"id": 1, "name": "test"}[k],
        )
        mock_record.keys = Mock(return_value=["id", "name"])
        mock_conn.fetchrow = AsyncMock(return_value=mock_record)

        conn = PostgresConnection(mock_conn, mock_monitor)

        result = await conn.fetch_one("SELECT * FROM test WHERE id = $1", (1,))

        assert result == {"id": 1, "name": "test"}
        mock_monitor.get_query_monitor.assert_called_once()

    @pytest.mark.asyncio
    async def test_postgres_connection_fetch_one_none_result(self):
        """Test PostgreSQL connection fetch_one with no results"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)

        conn = PostgresConnection(mock_conn)

        result = await conn.fetch_one("SELECT * FROM test WHERE id = $1", (999,))

        assert result is None

    @pytest.mark.asyncio
    async def test_postgres_connection_fetch_one_error(self):
        """Test PostgreSQL connection fetch_one error"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(
            side_effect=asyncpg.PostgresError("Table doesn't exist"),
        )

        conn = PostgresConnection(mock_conn)

        with pytest.raises(QueryError) as exc_info:
            await conn.fetch_one("SELECT * FROM nonexistent_table")

        error = exc_info.value
        assert "Query fetch failed" in str(error)
        assert error.details["query"] == "SELECT * FROM nonexistent_table"
        assert "Table doesn't exist" in error.details["error"]

    @pytest.mark.asyncio
    async def test_postgres_connection_fetch_all_without_monitoring(self):
        """Test PostgreSQL connection fetch_all without monitoring"""
        mock_conn = AsyncMock()
        mock_records = []
        for i in range(3):
            mock_record = Mock()

            # Create a closure with the current value of i
            def make_getitem(record_id):
                return lambda self, k: {"id": record_id, "name": f"test{record_id}"}[k]

            mock_record.__getitem__ = make_getitem(i + 1)
            mock_record.keys = Mock(return_value=["id", "name"])
            mock_records.append(mock_record)

        mock_conn.fetch = AsyncMock(return_value=mock_records)

        conn = PostgresConnection(mock_conn)

        result = await conn.fetch_all("SELECT * FROM test")

        assert len(result) == 3
        assert result[0] == {"id": 1, "name": "test1"}
        assert result[1] == {"id": 2, "name": "test2"}
        assert result[2] == {"id": 3, "name": "test3"}
        mock_conn.fetch.assert_called_once_with("SELECT * FROM test")

    @pytest.mark.asyncio
    async def test_postgres_connection_fetch_all_empty_result(self):
        """Test PostgreSQL connection fetch_all with empty results"""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])

        conn = PostgresConnection(mock_conn)

        result = await conn.fetch_all("SELECT * FROM test WHERE id = $1", (999,))

        assert result == []

    @pytest.mark.asyncio
    async def test_postgres_connection_fetch_all_with_monitoring(self, mock_monitor):
        """Test PostgreSQL connection fetch_all with monitoring"""
        mock_conn = AsyncMock()
        mock_records = []
        for i in range(2):
            mock_record = Mock()

            # Create a closure with the current value of i
            def make_getitem(record_id):
                return lambda self, k: {"id": record_id, "name": f"test{record_id}"}[k]

            mock_record.__getitem__ = make_getitem(i + 1)
            mock_record.keys = Mock(return_value=["id", "name"])
            mock_records.append(mock_record)

        mock_conn.fetch = AsyncMock(return_value=mock_records)

        conn = PostgresConnection(mock_conn, mock_monitor)

        result = await conn.fetch_all("SELECT * FROM test")

        assert len(result) == 2
        mock_monitor.get_query_monitor.assert_called_once()

    @pytest.mark.asyncio
    async def test_postgres_connection_fetch_all_error(self):
        """Test PostgreSQL connection fetch_all error"""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(
            side_effect=asyncpg.PostgresError("Permission denied"),
        )

        conn = PostgresConnection(mock_conn)

        with pytest.raises(QueryError) as exc_info:
            await conn.fetch_all("SELECT * FROM restricted_table")

        error = exc_info.value
        assert "Query fetch all failed" in str(error)
        assert error.details["query"] == "SELECT * FROM restricted_table"
        assert "Permission denied" in error.details["error"]

    @pytest.mark.asyncio
    async def test_postgres_connection_close(self):
        """Test PostgreSQL connection close"""
        mock_conn = AsyncMock()
        conn = PostgresConnection(mock_conn)

        await conn.close()  # Should not raise any errors

    @pytest.mark.asyncio
    async def test_postgres_pool_get_connection_error(self):
        """Test PostgreSQL pool get_connection error"""
        with patch("lexigram.sql.backends.postgres.asyncpg") as mock_asyncpg:
            mock_asyncpg.PostgresError = Exception
            mock_pool = AsyncMock()

            # Mock pool.acquire() to return an async context manager that raises exception
            class FailingAsyncContextManager:
                async def __aenter__(self):
                    raise Exception("Pool exhausted")

                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    pass

            mock_pool.acquire = Mock(return_value=FailingAsyncContextManager())
            mock_asyncpg.create_pool = AsyncMock(return_value=mock_pool)

            pool = PostgresConnectionPool("postgresql://user:pass@localhost:5432/test")
            await pool.initialize()

            # Mock circuit breaker
            mock_circuit_breaker = AsyncMock()

            @asynccontextmanager
            async def mock_protect():
                yield

            mock_circuit_breaker.protect = mock_protect
            pool.circuit_breaker = mock_circuit_breaker

            with pytest.raises(
                DatabaseConnectionError,
                match="Connection acquisition failed",
            ):
                async with pool.get_connection():
                    pass

            assert pool._error_count == 1
            assert pool._is_healthy is False

    @pytest.mark.asyncio
    async def test_postgres_pool_close(self):
        """Test PostgreSQL pool close"""
        with patch("lexigram.sql.backends.postgres.asyncpg") as mock_asyncpg:
            mock_asyncpg.PostgresError = Exception
            mock_pool = AsyncMock()
            mock_asyncpg.create_pool = AsyncMock(return_value=mock_pool)

            pool = PostgresConnectionPool("postgresql://user:pass@localhost:5432/test")
            await pool.initialize()

            await pool.shutdown()

            assert pool._pool is None
            assert pool._is_healthy is False
            mock_pool.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_postgres_pool_close_without_initialization(self):
        """Test PostgreSQL pool close without initialization"""
        pool = PostgresConnectionPool("postgresql://user:pass@localhost:5432/test")

        await pool.shutdown()  # Should not raise any errors

    @pytest.mark.asyncio
    async def test_postgres_pool_health_check_healthy(self):
        """Test PostgreSQL pool health check when healthy"""
        with patch("lexigram.sql.backends.postgres.asyncpg") as mock_asyncpg:
            mock_asyncpg.PostgresError = Exception
            mock_pool = AsyncMock()
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock(return_value="SELECT 1")

            # Mock pool.acquire() to return an async context manager
            @asynccontextmanager
            async def mock_acquire():
                yield mock_conn

            mock_pool.acquire = mock_acquire
            mock_asyncpg.create_pool = AsyncMock(return_value=mock_pool)

            pool = PostgresConnectionPool("postgresql://user:pass@localhost:5432/test")
            await pool.initialize()

            # Mock circuit breaker as async context manager
            mock_circuit_breaker = AsyncMock()

            @asynccontextmanager
            async def mock_protect():
                yield

            mock_circuit_breaker.protect = mock_protect
            mock_circuit_breaker.state = AsyncMock()
            mock_circuit_breaker.state.value = "closed"
            pool.circuit_breaker = mock_circuit_breaker

            health = await pool.health_check()

            assert health.status == HealthStatus.HEALTHY
            assert health.details.get("pool_size") == "10-20"
            assert health.details.get("connections_created") == 1
            assert "active_connections" in health.details
            assert "error_count" in health.details

    @pytest.mark.asyncio
    async def test_postgres_pool_health_check_unhealthy_no_pool(self):
        """Test PostgreSQL pool health check when pool not initialized"""
        pool = PostgresConnectionPool("postgresql://user:pass@localhost:5432/test")

        health = await pool.health_check()

        assert health.status == HealthStatus.UNHEALTHY
        assert "Pool not initialized" in (health.error or "")

    @pytest.mark.asyncio
    async def test_postgres_pool_health_check_unhealthy_query_failed(self):
        """Test PostgreSQL pool health check when query fails"""
        with patch("lexigram.sql.backends.postgres.asyncpg") as mock_asyncpg:
            mock_asyncpg.PostgresError = Exception
            mock_asyncpg.PostgresConnectionError = Exception
            mock_asyncpg.PostgresPoolAcquisitionError = Exception
            mock_pool = AsyncMock()

            # Mock pool.acquire() to return an async context manager that raises exception
            class FailingAsyncContextManager:
                async def __aenter__(self):
                    raise Exception("Connection failed")

                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    pass

            mock_pool.acquire = Mock(return_value=FailingAsyncContextManager())
            mock_asyncpg.create_pool = AsyncMock(return_value=mock_pool)

            pool = PostgresConnectionPool("postgresql://user:pass@localhost:5432/test")
            await pool.initialize()

            health = await pool.health_check()

            assert health.status == HealthStatus.UNHEALTHY
            assert health.error is not None
            assert health.details.get("error_count") == 1  # Health check error

    @pytest.mark.asyncio
    async def test_postgres_pool_health_check_caching(self):
        """Test PostgreSQL pool health check caching"""
        with patch("lexigram.sql.backends.postgres.asyncpg") as mock_asyncpg:
            mock_asyncpg.PostgresError = Exception
            mock_pool = AsyncMock()
            mock_conn = AsyncMock()
            mock_conn.execute = AsyncMock(return_value="SELECT 1")

            # Mock pool.acquire() to return an async context manager
            @asynccontextmanager
            async def mock_acquire():
                yield mock_conn

            mock_pool.acquire = mock_acquire
            mock_asyncpg.create_pool = AsyncMock(return_value=mock_pool)

            pool = PostgresConnectionPool("postgresql://user:pass@localhost:5432/test")
            await pool.initialize()

            # Mock circuit breaker as async context manager
            mock_circuit_breaker = AsyncMock()

            @asynccontextmanager
            async def mock_protect():
                yield

            mock_circuit_breaker.protect = mock_protect
            mock_circuit_breaker.state = AsyncMock()
            mock_circuit_breaker.state.value = "closed"
            pool.circuit_breaker = mock_circuit_breaker

            # First health check
            health1 = await pool.health_check()
            assert health1.status == HealthStatus.HEALTHY

            # Second health check (should be cached if within 30 seconds)
            await asyncio.sleep(0.01)  # Small delay
            health2 = await pool.health_check()

            # Should be the same result (cached)
            assert health2.status == HealthStatus.HEALTHY
            assert health2.details.get("cached") is True

    @pytest.mark.asyncio
    async def test_postgres_pool_get_stats(self):
        """Test PostgreSQL pool statistics"""
        pool = PostgresConnectionPool(
            "postgresql://user:pass@localhost:5432/test",
            min_size=5,
            max_size=25,
        )

        stats = await pool.get_pool_stats()

        assert stats["pool_size"] == "5-25"
        assert stats["is_initialized"] is False
        assert stats["is_healthy"] is False
        assert stats["total_connections_created"] == 0
        assert stats["active_connection_count"] == 0
        assert stats["error_count"] == 0
        assert "circuit_breaker_state" in stats
        assert "last_health_check" in stats

    @pytest.mark.asyncio
    async def test_postgres_pool_with_monitoring(self, mock_monitor):
        """Test PostgreSQL pool with monitoring enabled"""
        with patch("lexigram.sql.backends.postgres.asyncpg") as mock_asyncpg:
            mock_asyncpg.PostgresError = Exception
            mock_pool = AsyncMock()
            mock_asyncpg.create_pool = AsyncMock(return_value=mock_pool)

            pool = PostgresConnectionPool(
                "postgresql://user:pass@localhost:5432/test",
                monitor=mock_monitor,
            )
            await pool.initialize()

            assert pool.monitor == mock_monitor
            mock_monitor.start_pool_monitoring.assert_called_once()

            await pool.shutdown()
            mock_monitor.stop_pool_monitoring.assert_called_once()

    @pytest.mark.asyncio
    async def test_postgres_pool_retry_logic(self):
        """Test PostgreSQL pool retry logic on initialization failures"""
        with patch("lexigram.sql.backends.postgres.asyncpg") as mock_asyncpg:
            mock_asyncpg.PostgresError = Exception
            mock_asyncpg.create_pool = AsyncMock()
            # Mock retry to track calls

            with patch(
                "lexigram.sql.backends.postgres.retry_call", new_callable=AsyncMock
            ) as mock_retry:
                mock_pool = AsyncMock()
                mock_retry.return_value = mock_pool

                pool = PostgresConnectionPool(
                    "postgresql://user:pass@localhost:5432/test",
                )
                await pool.initialize()

                # Verify retry_async was called with correct parameters
                mock_retry.assert_called_once()
                call_args = mock_retry.call_args
                assert call_args[0][0] == pool._create_pool  # Function to retry
                assert call_args[1]["config"] == pool.retry_config  # Retry config

    @pytest.mark.asyncio
    async def test_postgres_pool_circuit_breaker(self):
        """Test PostgreSQL pool circuit breaker integration"""
        with patch("lexigram.sql.backends.postgres.asyncpg") as mock_asyncpg:
            mock_asyncpg.PostgresError = Exception
            mock_pool = AsyncMock()

            # Mock pool.acquire() to return an async context manager that raises exception
            class FailingAsyncContextManager:
                async def __aenter__(self):
                    raise Exception("Connection failed")

                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    pass

            mock_pool.acquire = Mock(return_value=FailingAsyncContextManager())
            mock_asyncpg.create_pool = AsyncMock(return_value=mock_pool)

            pool = PostgresConnectionPool("postgresql://user:pass@localhost:5432/test")
            await pool.initialize()

            # Mock circuit breaker
            mock_circuit_breaker = Mock()

            @asynccontextmanager
            async def mock_protect():
                yield

            mock_circuit_breaker.protect = Mock(side_effect=mock_protect)
            pool.circuit_breaker = mock_circuit_breaker

            with pytest.raises(DatabaseConnectionError):
                async with pool.get_connection():
                    pass

            # Verify circuit breaker was used
            mock_circuit_breaker.protect.assert_called_once()

    @pytest.mark.asyncio
    async def test_postgres_connection_with_custom_monitor(self, mock_monitor):
        """Test PostgreSQL connection with custom monitor"""
        mock_conn = AsyncMock()
        conn = PostgresConnection(mock_conn, mock_monitor)

        assert conn.monitor == mock_monitor
        assert conn.connection_id.startswith("postgres_")

    def test_postgres_import_error_when_unavailable(self):
        """Test PostgreSQL import error when asyncpg not available"""
        with patch("lexigram.sql.backends.postgres.HAS_POSTGRES", False):
            with pytest.raises(
                ImportError,
                match="asyncpg is required for PostgreSQL support",
            ):
                PostgresConnectionPool(
                    host="localhost",
                    port=5432,
                    user="user",
                    password="pass",
                    database="test",
                )

    @pytest.mark.asyncio
    async def test_postgres_factory_function(self):
        """Test create_postgres_pool factory function"""
        mock_monitor = Mock()
        mock_monitor.start_pool_monitoring = AsyncMock()

        pool = create_postgres_pool(
            host="postgres.example.com",
            port=5432,
            user="admin",
            password="secret",
            database="production",
            min_size=5,
            max_size=50,
            ssl={"verify_cert": False},
            monitor=mock_monitor,
        )

        assert isinstance(pool, PostgresConnectionPool)
        assert pool.host == "postgres.example.com"
        assert pool.database == "production"

        assert pool.min_size == 5
        assert pool.max_size == 50
        assert pool.ssl == {"verify_cert": False}

        assert pool.monitor == mock_monitor

    @pytest.mark.asyncio
    async def test_postgres_connection_error_details(self):
        """Test PostgreSQL connection error includes query details"""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(side_effect=Exception("Network timeout"))

        conn = PostgresConnection(mock_conn)

        with pytest.raises(DatabaseConnectionError) as exc_info:
            await conn.execute("SELECT * FROM large_table", (1, 2, 3))

        error = exc_info.value
        assert "Connection error" in str(error)
        assert error.details["query"] == "SELECT * FROM large_table"
        assert "Network timeout" in error.details["error"]

    @pytest.mark.asyncio
    async def test_postgres_fetch_error_details(self):
        """Test PostgreSQL fetch error includes query details"""
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(
            side_effect=asyncpg.PostgresError("Column doesn't exist"),
        )

        conn = PostgresConnection(mock_conn)

        with pytest.raises(QueryError) as exc_info:
            await conn.fetch_one("SELECT nonexistent_column FROM test", (1,))

        error = exc_info.value
        assert "Query fetch failed" in str(error)
        assert error.details["query"] == "SELECT nonexistent_column FROM test"
        assert "Column doesn't exist" in error.details["error"]

    @pytest.mark.asyncio
    async def test_postgres_execute_many_error_details(self):
        """Test PostgreSQL execute_many error includes query details"""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(
            side_effect=asyncpg.PostgresError("Duplicate key"),
        )

        # Mock transaction as async context manager
        @asynccontextmanager
        async def mock_transaction():
            yield

        mock_conn.transaction = mock_transaction

        conn = PostgresConnection(mock_conn)

        params_list = [("value1",), ("value2",)]
        with pytest.raises(QueryError) as exc_info:
            await conn.execute_many("INSERT INTO unique_table VALUES ($1)", params_list)

        error = exc_info.value
        assert "Batch execution failed" in str(error)
        assert error.details["query"] == "INSERT INTO unique_table VALUES ($1)"
        assert "Duplicate key" in error.details["error"]
