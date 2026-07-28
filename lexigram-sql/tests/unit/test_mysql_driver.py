"""Comprehensive tests for MySQL database driver"""

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock, patch

import pytest

from lexigram.contracts.core import HealthStatus

try:
    import aiomysql

    HAS_MYSQL = True
except ImportError:
    HAS_MYSQL = False
    aiomysql = None  # type: ignore[assignment]

from lexigram.sql.backends.mysql import (
    HAS_MYSQL,
    MySQLConnection,
    MySQLConnectionPool,
    create_mysql_pool,
)
from lexigram.sql.exceptions import DatabaseConnectionError, QueryError


@pytest.mark.skipif(not HAS_MYSQL, reason="aiomysql not available")
class TestMySQLDriver:
    @pytest.fixture
    def mock_monitor(self):
        """Create a mock monitor"""
        monitor = Mock()
        query_monitor = Mock()

        # Create a proper async context manager
        @asynccontextmanager
        async def monitor_query(*args, **kwargs):
            yield Mock()

        query_monitor.monitor_query = monitor_query
        monitor.get_query_monitor.return_value = query_monitor
        monitor.start_pool_monitoring = AsyncMock()
        monitor.stop_pool_monitoring = AsyncMock()
        return monitor

    def test_mysql_pool_creation(self):
        """Test MySQL pool creation with various parameters"""
        # Basic creation
        pool = create_mysql_pool(
            host="localhost",
            user="root",
            password="pass",
            database="test",
        )
        assert isinstance(pool, MySQLConnectionPool)
        assert pool.host == "localhost"
        assert pool.user == "root"
        assert pool.password == "pass"
        assert pool.database == "test"
        assert pool.port == 3306  # default
        assert pool.min_size == 10  # default
        assert pool.max_size == 20  # default

        # Custom parameters
        pool = MySQLConnectionPool(
            host="mysql.example.com",
            port=3307,
            user="admin",
            password="secret",
            database="production",
            min_size=5,
            max_size=50,
            ssl={"ca": "/path/to/ca.pem"},
        )
        assert pool.host == "mysql.example.com"
        assert pool.port == 3307
        assert pool.user == "admin"
        assert pool.database == "production"
        assert pool.min_size == 5
        assert pool.max_size == 50
        assert pool.ssl == {"ca": "/path/to/ca.pem"}

    @pytest.mark.asyncio
    async def test_mysql_pool_initialization_success(self):
        """Test successful MySQL pool initialization"""
        mock_pool = AsyncMock()

        pool = MySQLConnectionPool("localhost", 3306, "root", "pass", "test")

        # Mock the _create_pool method to avoid aiomysql.create_pool call
        async def mock_create_pool(pool_kwargs):
            pool._pool = mock_pool
            pool._total_connections_created += 1
            pool._is_healthy = True

        with patch.object(pool, "_create_pool", side_effect=mock_create_pool):
            await pool.initialize()

            assert pool._pool == mock_pool
            assert pool._is_healthy is True
            assert pool._total_connections_created == 1

    @pytest.mark.asyncio
    async def test_mysql_pool_initialization_with_ssl(self):
        """Test MySQL pool initialization with SSL configuration"""
        mock_pool = AsyncMock()

        ssl_config = {"ca": "/path/to/ca.pem", "cert": "/path/to/client-cert.pem"}
        pool = MySQLConnectionPool(
            "localhost",
            3306,
            "root",
            "pass",
            "test",
            ssl=ssl_config,
        )

        # Mock the _create_pool method
        async def mock_create_pool(pool_kwargs):
            pool._pool = mock_pool
            pool._total_connections_created += 1
            pool._is_healthy = True

        with patch.object(pool, "_create_pool", side_effect=mock_create_pool):
            await pool.initialize()

            # Verify SSL config was passed to aiomysql (would be in pool_kwargs)
            assert pool.ssl == ssl_config

    @pytest.mark.asyncio
    async def test_mysql_pool_initialization_failure(self):
        """Test MySQL pool initialization failure"""
        pool = MySQLConnectionPool("localhost", 3306, "root", "pass", "test")

        # Mock the _create_pool method to raise DatabaseConnectionError
        async def failing_create_pool(pool_kwargs):
            raise DatabaseConnectionError("Connection failed")

        # Mock retry_async to actually call the function and let it raise
        async def failing_retry_async(func, config, *args, **kwargs):
            return await func(*args, **kwargs)

        with patch.object(pool, "_create_pool", side_effect=failing_create_pool):
            with pytest.raises(DatabaseConnectionError, match="Connection failed"):
                await pool.initialize()

            assert pool._is_healthy is False
            assert pool._error_count == 0  # Error count is not incremented in this case

    @pytest.mark.asyncio
    async def test_mysql_pool_double_initialization(self):
        """Test that pool initialization is idempotent"""
        mock_pool = AsyncMock()

        pool = MySQLConnectionPool("localhost", 3306, "root", "pass", "test")

        # Mock the _create_pool method
        async def mock_create_pool(pool_kwargs):
            pool._pool = mock_pool
            pool._total_connections_created += 1
            pool._is_healthy = True

        with patch.object(pool, "_create_pool", side_effect=mock_create_pool):
            await pool.initialize()
            await pool.initialize()  # Should not create another pool

            # Should only be called once
            assert pool._total_connections_created == 1

    @pytest.mark.asyncio
    async def test_mysql_connection_creation(self):
        """Test MySQL connection creation from pool"""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()

        pool = MySQLConnectionPool("localhost", 3306, "root", "pass", "test")

        # Mock the _create_pool method
        async def mock_create_pool(pool_kwargs):
            pool._pool = mock_pool
            pool._total_connections_created += 1
            pool._is_healthy = True

        # Create an async context manager for pool.acquire()
        class MockAcquireContext:
            async def __aenter__(self):
                return mock_conn

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        mock_pool.acquire = Mock(return_value=MockAcquireContext())

        with patch.object(pool, "_create_pool", side_effect=mock_create_pool):
            await pool.initialize()

            # Mock circuit breaker as async context manager
            @asynccontextmanager
            async def mock_circuit_breaker():
                yield

            pool.circuit_breaker = mock_circuit_breaker()

            async with pool.get_connection() as conn:
                assert isinstance(conn, MySQLConnection)
                assert conn._conn == mock_conn
                assert conn.connection_id.startswith("mysql_")

            # Verify connection was acquired and released
            # Note: We can't easily verify the call counts with the context manager mock

    @pytest.mark.asyncio
    async def test_mysql_connection_execute_without_monitoring(self):
        """Test MySQL connection execute method without monitoring"""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=None)
        mock_conn.affected_rows = 5

        conn = MySQLConnection(mock_conn)

        # Execute without parameters
        result = await conn.execute("CREATE TABLE test (id INT)")
        assert result == 5
        mock_conn.execute.assert_called_with("CREATE TABLE test (id INT)")

        # Execute with parameters
        mock_conn.execute.reset_mock()
        result = await conn.execute("INSERT INTO test VALUES (?)", (1,))
        assert result == 5
        mock_conn.execute.assert_called_with("INSERT INTO test VALUES (?)", (1,))

    @pytest.mark.asyncio
    async def test_mysql_connection_execute_with_monitoring(self, mock_monitor):
        """Test MySQL connection execute method with monitoring"""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=None)
        mock_conn.affected_rows = 3

        conn = MySQLConnection(mock_conn, mock_monitor)

        result = await conn.execute("UPDATE test SET name = ?", ("new_name",))
        assert result == 3

        # Verify monitoring was called
        mock_monitor.get_query_monitor.assert_called_once()
        # The monitor_query context manager should have been used

    @pytest.mark.asyncio
    async def test_mysql_connection_execute_error(self):
        """Test MySQL connection execute error handling"""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(side_effect=aiomysql.Error("Query failed"))

        conn = MySQLConnection(mock_conn)

        with pytest.raises(QueryError, match="Query execution failed"):
            await conn.execute("INVALID QUERY")

    @pytest.mark.asyncio
    async def test_mysql_connection_execute_many(self):
        """Test MySQL connection execute_many method"""
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()

        # Mock cursor() to return a context manager that accepts arguments
        @asynccontextmanager
        async def mock_cursor_context(*args, **kwargs):
            yield mock_cursor

        mock_conn.cursor = mock_cursor_context

        conn = MySQLConnection(mock_conn)

        params_list = [("value1",), ("value2",), ("value3",)]
        await conn.execute_many("INSERT INTO test VALUES (?)", params_list)

        # Verify cursor was used correctly
        mock_cursor.executemany.assert_called_once_with(
            "INSERT INTO test VALUES (?)",
            params_list,
        )
        mock_conn.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_mysql_connection_execute_many_error(self):
        """Test MySQL connection execute_many error handling"""
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()

        # Mock cursor() to return a context manager
        @asynccontextmanager
        async def mock_cursor_context(*args, **kwargs):
            yield mock_cursor

        mock_conn.cursor = mock_cursor_context
        mock_cursor.executemany = AsyncMock(
            side_effect=aiomysql.Error("Batch insert failed"),
        )

        conn = MySQLConnection(mock_conn)

        with pytest.raises(QueryError, match="Batch execution failed"):
            await conn.execute_many("INSERT INTO test VALUES (?)", [("value1",)])

    @pytest.mark.asyncio
    async def test_mysql_connection_fetch_one_without_monitoring(self):
        """Test MySQL connection fetch_one method without monitoring"""
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value={"id": 1, "name": "test"})

        # Mock cursor() to return a context manager that accepts arguments
        @asynccontextmanager
        async def mock_cursor_context(*args, **kwargs):
            yield mock_cursor

        mock_conn.cursor = mock_cursor_context

        conn = MySQLConnection(mock_conn)

        # Fetch without parameters
        result = await conn.fetch_one("SELECT * FROM test LIMIT 1")
        assert result == {"id": 1, "name": "test"}
        mock_cursor.execute.assert_called_with("SELECT * FROM test LIMIT 1")

        # Fetch with parameters
        mock_cursor.fetchone.reset_mock()
        mock_cursor.execute.reset_mock()
        result = await conn.fetch_one("SELECT * FROM test WHERE id = ?", (1,))
        assert result == {"id": 1, "name": "test"}
        mock_cursor.execute.assert_called_with("SELECT * FROM test WHERE id = ?", (1,))

    @pytest.mark.asyncio
    async def test_mysql_connection_fetch_one_with_monitoring(self, mock_monitor):
        """Test MySQL connection fetch_one method with monitoring"""
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value={"id": 1, "name": "test"})

        # Mock cursor() to return a context manager that accepts arguments
        @asynccontextmanager
        async def mock_cursor_context(*args, **kwargs):
            yield mock_cursor

        mock_conn.cursor = mock_cursor_context

        conn = MySQLConnection(mock_conn, mock_monitor)

        result = await conn.fetch_one("SELECT * FROM test WHERE id = ?", (1,))
        assert result == {"id": 1, "name": "test"}

        # Verify monitoring was called
        mock_monitor.get_query_monitor.assert_called_once()

    @pytest.mark.asyncio
    async def test_mysql_connection_fetch_one_none_result(self):
        """Test MySQL connection fetch_one with no results"""
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=None)

        # Mock cursor() to return a context manager that accepts arguments
        @asynccontextmanager
        async def mock_cursor_context(*args, **kwargs):
            yield mock_cursor

        mock_conn.cursor = mock_cursor_context

        conn = MySQLConnection(mock_conn)

        result = await conn.fetch_one("SELECT * FROM test WHERE id = ?", (999,))
        assert result is None

    @pytest.mark.asyncio
    async def test_mysql_connection_fetch_one_error(self):
        """Test MySQL connection fetch_one error handling"""
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()

        # Mock cursor() to return a context manager
        @asynccontextmanager
        async def mock_cursor_context(*args, **kwargs):
            yield mock_cursor

        mock_conn.cursor = mock_cursor_context
        mock_cursor.execute = AsyncMock(side_effect=aiomysql.Error("Fetch failed"))

        conn = MySQLConnection(mock_conn)

        with pytest.raises(QueryError, match="Query fetch failed"):
            await conn.fetch_one("SELECT * FROM nonexistent")

    @pytest.mark.asyncio
    async def test_mysql_connection_fetch_all_without_monitoring(self):
        """Test MySQL connection fetch_all method without monitoring"""
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(
            return_value=[{"id": 1, "name": "test1"}, {"id": 2, "name": "test2"}],
        )

        # Mock cursor() to return a context manager that accepts arguments
        @asynccontextmanager
        async def mock_cursor_context(*args, **kwargs):
            yield mock_cursor

        mock_conn.cursor = mock_cursor_context

        conn = MySQLConnection(mock_conn)

        # Fetch without parameters
        result = await conn.fetch_all("SELECT * FROM test")
        assert result == [{"id": 1, "name": "test1"}, {"id": 2, "name": "test2"}]

        # Fetch with parameters
        mock_cursor.fetchall.reset_mock()
        mock_cursor.execute.reset_mock()
        result = await conn.fetch_all(
            "SELECT * FROM test WHERE status = ?",
            ("active",),
        )
        assert result == [{"id": 1, "name": "test1"}, {"id": 2, "name": "test2"}]

    @pytest.mark.asyncio
    async def test_mysql_connection_fetch_all_empty_result(self):
        """Test MySQL connection fetch_all with empty results"""
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=[])

        # Mock cursor() to return a context manager that accepts arguments
        @asynccontextmanager
        async def mock_cursor_context(*args, **kwargs):
            yield mock_cursor

        mock_conn.cursor = mock_cursor_context

        conn = MySQLConnection(mock_conn)

        result = await conn.fetch_all("SELECT * FROM test WHERE id > ?", (100,))
        assert result == []

    @pytest.mark.asyncio
    async def test_mysql_connection_fetch_all_with_monitoring(self, mock_monitor):
        """Test MySQL connection fetch_all method with monitoring"""
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=[{"id": 1, "name": "test"}])

        # Mock cursor() to return a context manager that accepts arguments
        @asynccontextmanager
        async def mock_cursor_context(*args, **kwargs):
            yield mock_cursor

        mock_conn.cursor = mock_cursor_context

        conn = MySQLConnection(mock_conn, mock_monitor)

        result = await conn.fetch_all("SELECT * FROM test")
        assert result == [{"id": 1, "name": "test"}]

        # Verify monitoring was called
        mock_monitor.get_query_monitor.assert_called_once()

    @pytest.mark.asyncio
    async def test_mysql_connection_fetch_all_error(self):
        """Test MySQL connection fetch_all error handling"""
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()

        # Mock cursor() to return a context manager
        @asynccontextmanager
        async def mock_cursor_context(*args, **kwargs):
            yield mock_cursor

        mock_conn.cursor = mock_cursor_context
        mock_cursor.execute = AsyncMock(side_effect=aiomysql.Error("Fetch all failed"))

        conn = MySQLConnection(mock_conn)

        with pytest.raises(QueryError, match="Query fetch all failed"):
            await conn.fetch_all("SELECT * FROM nonexistent")

    @pytest.mark.asyncio
    async def test_mysql_connection_close(self):
        """Test MySQL connection close method (should be no-op)"""
        mock_conn = AsyncMock()
        conn = MySQLConnection(mock_conn)

        # Close should not raise exception (it's a no-op for MySQL connections)
        await conn.close()

    @pytest.mark.asyncio
    async def test_mysql_pool_get_connection_error(self):
        """Test MySQL pool get_connection error handling"""
        mock_pool = AsyncMock()

        pool = MySQLConnectionPool("localhost", 3306, "root", "pass", "test")

        # Mock the _create_pool method
        async def mock_create_pool(pool_kwargs):
            pool._pool = mock_pool
            pool._total_connections_created += 1
            pool._is_healthy = True

        # Mock pool.acquire() to return an async context manager that raises exception
        class FailingAsyncContextManager:
            async def __aenter__(self):
                raise Exception("Connection failed")

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        mock_pool.acquire = Mock(return_value=FailingAsyncContextManager())

        with patch.object(pool, "_create_pool", side_effect=mock_create_pool):
            await pool.initialize()

            # Mock circuit breaker as async context manager
            @asynccontextmanager
            async def mock_circuit_breaker():
                yield

            pool.circuit_breaker = mock_circuit_breaker()

            with pytest.raises(
                DatabaseConnectionError,
                match="Connection acquisition failed",
            ):
                async with pool.get_connection():
                    pass

            assert pool._error_count == 1

    @pytest.mark.asyncio
    async def test_mysql_pool_close(self):
        """Test MySQL pool close method"""
        mock_pool = AsyncMock()
        mock_pool.close = Mock()  # close() is synchronous
        mock_pool.wait_closed = AsyncMock()  # wait_closed() is async

        pool = MySQLConnectionPool("localhost", 3306, "root", "pass", "test")

        # Mock the _create_pool method
        async def mock_create_pool(pool_kwargs):
            pool._pool = mock_pool
            pool._total_connections_created += 1
            pool._is_healthy = True

        with patch.object(pool, "_create_pool", side_effect=mock_create_pool):
            await pool.initialize()

            assert pool._pool is not None
            assert pool._is_healthy is True

            await pool.shutdown()

            assert pool._pool is None
            assert pool._is_healthy is False
            mock_pool.close.assert_called_once()
            mock_pool.wait_closed.assert_called_once()

    @pytest.mark.asyncio
    async def test_mysql_pool_close_without_initialization(self):
        """Test MySQL pool close when not initialized"""
        pool = MySQLConnectionPool("localhost", 3306, "root", "pass", "test")

        # Should not raise exception
        await pool.shutdown()
        assert pool._pool is None

    @pytest.mark.asyncio
    async def test_mysql_pool_health_check_healthy(self):
        """Test MySQL pool health check when healthy"""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=None)
        mock_conn.affected_rows = 1

        pool = MySQLConnectionPool("localhost", 3306, "root", "pass", "test")

        # Mock the _create_pool method
        async def mock_create_pool(pool_kwargs):
            pool._pool = mock_pool
            pool._total_connections_created += 1
            pool._is_healthy = True

        # Create an async context manager for pool.acquire()
        class MockAcquireContext:
            async def __aenter__(self):
                return mock_conn

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        mock_pool.acquire = Mock(return_value=MockAcquireContext())

        with patch.object(pool, "_create_pool", side_effect=mock_create_pool):
            await pool.initialize()

            # Mock circuit breaker as async context manager for get_connection
            mock_cb = AsyncMock()
            mock_cb.state.value = "closed"
            mock_cb.__aenter__ = AsyncMock()
            mock_cb.__aexit__ = AsyncMock()

            pool.circuit_breaker = mock_cb

            health = await pool.health_check()

            assert health.status == HealthStatus.HEALTHY
            assert health.details.get("host") == "localhost:3306"
            assert health.details.get("database") == "test"
            assert health.details.get("pool_size") == "10-20"
            assert health.details.get("connections_created") == 1
            assert "active_connections" in health.details
            assert "error_count" in health.details

    @pytest.mark.asyncio
    async def test_mysql_pool_health_check_unhealthy_no_pool(self):
        """Test MySQL pool health check when pool not initialized"""
        pool = MySQLConnectionPool("localhost", 3306, "root", "pass", "test")

        health = await pool.health_check()

        assert health.status == HealthStatus.UNHEALTHY
        assert "Pool not initialized" in (health.error or "")

    @pytest.mark.asyncio
    async def test_mysql_pool_health_check_unhealthy_query_failed(self):
        """Test MySQL pool health check when query fails"""
        mock_pool = AsyncMock()

        pool = MySQLConnectionPool("localhost", 3306, "root", "pass", "test")

        # Mock the _create_pool method
        async def mock_create_pool(pool_kwargs):
            pool._pool = mock_pool
            pool._total_connections_created += 1
            pool._is_healthy = True

        # Mock pool.acquire() to return an async context manager that raises exception
        class FailingAsyncContextManager:
            async def __aenter__(self):
                raise Exception("Connection failed")

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        mock_pool.acquire = Mock(return_value=FailingAsyncContextManager())

        with patch.object(pool, "_create_pool", side_effect=mock_create_pool):
            await pool.initialize()

            health = await pool.health_check()

            assert health.status == HealthStatus.UNHEALTHY
            assert health.error is not None
            assert health.details.get("error_count") == 1

    @pytest.mark.asyncio
    async def test_mysql_pool_health_check_caching(self):
        """Test MySQL pool health check caching"""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(return_value=None)
        mock_conn.affected_rows = 1

        pool = MySQLConnectionPool("localhost", 3306, "root", "pass", "test")

        # Mock the _create_pool method
        async def mock_create_pool(pool_kwargs):
            pool._pool = mock_pool
            pool._total_connections_created += 1
            pool._is_healthy = True

        # Create an async context manager for pool.acquire()
        class MockAcquireContext:
            async def __aenter__(self):
                return mock_conn

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        mock_pool.acquire = Mock(return_value=MockAcquireContext())

        with patch.object(pool, "_create_pool", side_effect=mock_create_pool):
            await pool.initialize()

            # Mock circuit breaker as async context manager for get_connection
            mock_cb = AsyncMock()
            mock_cb.state.value = "closed"
            mock_cb.__aenter__ = AsyncMock()
            mock_cb.__aexit__ = AsyncMock()

            pool.circuit_breaker = mock_cb

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
    async def test_mysql_pool_get_stats(self):
        """Test MySQL pool statistics"""
        pool = MySQLConnectionPool(
            "localhost",
            3306,
            "root",
            "pass",
            "test",
            min_size=5,
            max_size=25,
        )

        stats = await pool.get_pool_stats()

        assert stats["host"] == "localhost:3306"
        assert stats["database"] == "test"
        assert stats["pool_size"] == "5-25"
        assert stats["is_initialized"] is False
        assert stats["is_healthy"] is False
        assert stats["total_connections_created"] == 0
        assert stats["active_connection_count"] == 0
        assert stats["error_count"] == 0
        assert "circuit_breaker_state" in stats
        assert "last_health_check" in stats

    @pytest.mark.asyncio
    async def test_mysql_pool_with_monitoring(self, mock_monitor):
        """Test MySQL pool with monitoring enabled"""
        mock_pool = AsyncMock()
        mock_pool.close = Mock()  # close() is synchronous

        pool = MySQLConnectionPool(
            "localhost",
            3306,
            "root",
            "pass",
            "test",
            monitor=mock_monitor,
        )

        # Mock the _create_pool method
        async def mock_create_pool(pool_kwargs):
            pool._pool = mock_pool
            pool._total_connections_created += 1
            pool._is_healthy = True

        with patch.object(pool, "_create_pool", side_effect=mock_create_pool):
            await pool.initialize()

            assert pool.monitor == mock_monitor
            mock_monitor.start_pool_monitoring.assert_called_once()

            await pool.shutdown()
            mock_monitor.stop_pool_monitoring.assert_called_once()

    @pytest.mark.asyncio
    async def test_mysql_pool_retry_logic(self):
        """Test MySQL pool retry logic on initialization failures"""
        mock_pool = AsyncMock()

        pool = MySQLConnectionPool("localhost", 3306, "root", "pass", "test")

        # Mock the _create_pool method to fail twice then succeed
        call_count = 0

        async def mock_create_pool(pool_kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Connection failed")
            pool._pool = mock_pool
            pool._total_connections_created += 1
            pool._is_healthy = True
            return mock_pool

        with patch.object(pool, "_create_pool", side_effect=mock_create_pool):
            await pool.initialize()

            # Verify _create_pool was called 3 times (2 failures + 1 success)
            assert call_count == 3
            assert pool._pool == mock_pool
            assert pool._is_healthy is True

    @pytest.mark.asyncio
    async def test_mysql_pool_circuit_breaker(self):
        """Test MySQL pool circuit breaker integration"""
        mock_pool = AsyncMock()

        pool = MySQLConnectionPool("localhost", 3306, "root", "pass", "test")

        # Mock the _create_pool method
        async def mock_create_pool(pool_kwargs):
            pool._pool = mock_pool
            pool._total_connections_created += 1
            pool._is_healthy = True

        # Mock pool.acquire() to return an async context manager that raises exception
        class FailingAsyncContextManager:
            async def __aenter__(self):
                raise Exception("Connection failed")

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        mock_pool.acquire = Mock(return_value=FailingAsyncContextManager())

        with patch.object(pool, "_create_pool", side_effect=mock_create_pool):
            await pool.initialize()

            # Mock circuit breaker
            pool.circuit_breaker = AsyncMock()

            with pytest.raises(DatabaseConnectionError):
                async with pool.get_connection():
                    pass

            # Verify circuit breaker was used
            pool.circuit_breaker.__aenter__.assert_called_once()

    @pytest.mark.asyncio
    async def test_mysql_connection_with_custom_monitor(self, mock_monitor):
        """Test MySQL connection with custom monitor"""
        mock_conn = AsyncMock()
        conn = MySQLConnection(mock_conn, mock_monitor)

        assert conn.monitor == mock_monitor
        assert conn.connection_id.startswith("mysql_")

    def test_mysql_import_error_when_unavailable(self):
        """Test MySQL import error when aiomysql not available"""
        with patch("lexigram.sql.backends.mysql.HAS_MYSQL", False):
            with pytest.raises(
                ImportError,
                match="aiomysql is required for MySQL support",
            ):
                MySQLConnectionPool("localhost", 3306, "root", "pass", "test")

    @pytest.mark.asyncio
    async def test_mysql_factory_function(self):
        """Test create_mysql_pool factory function"""
        mock_monitor = Mock()
        mock_monitor.start_pool_monitoring = AsyncMock()

        pool = create_mysql_pool(
            host="mysql.example.com",
            port=3307,
            user="admin",
            password="secret",
            database="production",
            min_size=5,
            max_size=50,
            ssl={"ca": "/path/to/ca.pem"},
            monitor=mock_monitor,
        )

        assert isinstance(pool, MySQLConnectionPool)
        assert pool.host == "mysql.example.com"
        assert pool.port == 3307
        assert pool.user == "admin"
        assert pool.database == "production"
        assert pool.min_size == 5
        assert pool.max_size == 50
        assert pool.ssl == {"ca": "/path/to/ca.pem"}
        assert pool.monitor == mock_monitor

    @pytest.mark.asyncio
    async def test_mysql_connection_error_details(self):
        """Test MySQL connection error includes query details"""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(side_effect=Exception("Syntax error"))

        conn = MySQLConnection(mock_conn)

        with pytest.raises(QueryError) as exc_info:
            await conn.execute("INVALID SQL QUERY", ("param1", "param2"))

        error = exc_info.value
        assert "Query execution failed" in str(error)
        assert error.details["query"] == "INVALID SQL QUERY"
        assert "Syntax error" in error.details["error"]

    @pytest.mark.asyncio
    async def test_mysql_fetch_error_details(self):
        """Test MySQL fetch error includes query details"""
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.execute = AsyncMock(side_effect=Exception("Table doesn't exist"))

        # Mock cursor() to return a context manager that accepts arguments
        @asynccontextmanager
        async def mock_cursor_context(*args, **kwargs):
            yield mock_cursor

        mock_conn.cursor = mock_cursor_context

        conn = MySQLConnection(mock_conn)

        with pytest.raises(QueryError) as exc_info:
            await conn.fetch_one("SELECT * FROM nonexistent_table", (1,))

        error = exc_info.value
        assert "Query fetch failed" in str(error)
        assert error.details["query"] == "SELECT * FROM nonexistent_table"
        assert "Table doesn't exist" in error.details["error"]

    @pytest.mark.asyncio
    async def test_mysql_execute_many_error_details(self):
        """Test MySQL execute_many error includes query details"""
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.executemany = AsyncMock(
            side_effect=Exception("Constraint violation"),
        )

        # Mock cursor() to return a context manager that accepts arguments
        @asynccontextmanager
        async def mock_cursor_context(*args, **kwargs):
            yield mock_cursor

        mock_conn.cursor = mock_cursor_context

        conn = MySQLConnection(mock_conn)

        params_list = [("value1",), ("value2",)]
        with pytest.raises(QueryError) as exc_info:
            await conn.execute_many("INSERT INTO test VALUES (?)", params_list)

        error = exc_info.value
        assert "Batch execution failed" in str(error)
        assert error.details["query"] == "INSERT INTO test VALUES (?)"
        assert "Constraint violation" in error.details["error"]
