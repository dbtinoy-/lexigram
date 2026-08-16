"""Tests for SQLite database driver"""

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock, patch

import pytest

try:
    import aiosqlite

    HAS_SQLITE = True
except ImportError:
    HAS_SQLITE = False
    aiosqlite = None  # type: ignore[assignment]

from lexigram.contracts import HealthStatus
from lexigram.sql.backends.sqlite import (
    HAS_SQLITE,
    SQLiteConnection,
    SQLiteConnectionPool,
    create_sqlite_pool,
)
from lexigram.sql.exceptions import DatabaseConnectionError, QueryError


@pytest.mark.skipif(not HAS_SQLITE, reason="aiosqlite not available")
class TestSQLiteDriver:
    """Test SQLite driver functionality"""

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

        monitor_query_mock.side_effect = monitor_query
        query_monitor.monitor_query = monitor_query_mock
        monitor.get_query_monitor.return_value = query_monitor
        monitor.start_pool_monitoring = AsyncMock()
        monitor.stop_pool_monitoring = AsyncMock()
        monitor.get_stats = AsyncMock(return_value={})
        return monitor

    @pytest.mark.asyncio
    async def test_sqlite_pool_creation(self):
        """Test SQLite pool creation"""
        with patch("lexigram.sql.backends.sqlite.aiosqlite") as mock_aiosqlite:
            mock_conn = AsyncMock()
            mock_aiosqlite.connect = AsyncMock(return_value=mock_conn)

            pool = SQLiteConnectionPool(":memory:")
            await pool.initialize()

            mock_aiosqlite.connect.assert_called_once()
            call_args = mock_aiosqlite.connect.call_args
            assert call_args[0][0] == ":memory:"

    @pytest.mark.asyncio
    async def test_sqlite_pool_initialization_success(self):
        """Test SQLite pool initialization success"""
        with patch("lexigram.sql.backends.sqlite.aiosqlite") as mock_aiosqlite:
            mock_conn = AsyncMock()
            mock_aiosqlite.connect = AsyncMock(return_value=mock_conn)

            pool = SQLiteConnectionPool("test.db")
            await pool.initialize()

            assert pool._conn is not None
            assert pool._is_healthy is True
            assert pool._total_connections_created == 1

    @pytest.mark.asyncio
    async def test_sqlite_pool_initialization_failure(self):
        """Test SQLite pool initialization failure"""
        with patch("lexigram.sql.backends.sqlite.aiosqlite") as mock_aiosqlite:
            mock_aiosqlite.connect = AsyncMock(
                side_effect=OSError("Connection failed"),
            )

            # Mock retry_call to avoid retries in this test
            with patch(
                "lexigram.sql.backends.sqlite.retry_call", new_callable=AsyncMock
            ) as mock_retry:
                mock_retry.side_effect = OSError("Connection failed")

                pool = SQLiteConnectionPool("test.db")

                with pytest.raises(OSError, match="Connection failed"):
                    await pool.initialize()

            assert pool._conn is None
            assert pool._is_healthy is False

            mock_conn = AsyncMock()
            mock_aiosqlite.connect = AsyncMock(return_value=mock_conn)

            pool = SQLiteConnectionPool("test.db")
            await pool.initialize()
            await pool.initialize()  # Should not create connection again

            # Should only be called once
            mock_aiosqlite.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_sqlite_connection_creation(self):
        """Test SQLite connection creation"""
        with patch("lexigram.sql.backends.sqlite.aiosqlite") as mock_aiosqlite:
            mock_conn = AsyncMock()
            mock_aiosqlite.connect = AsyncMock(return_value=mock_conn)

            pool = SQLiteConnectionPool("test.db")
            await pool.initialize()

            # Mock circuit breaker as async context manager
            mock_circuit_breaker = Mock()

            @asynccontextmanager
            async def mock_protect():
                yield

            mock_circuit_breaker.protect = Mock(side_effect=mock_protect)
            pool.circuit_breaker = mock_circuit_breaker

            async with pool.get_connection() as conn:
                assert isinstance(conn, SQLiteConnection)
                assert conn._conn == mock_conn
                assert pool._connection_count == 1

    @pytest.mark.asyncio
    async def test_sqlite_connection_execute_select_without_monitoring(self):
        """Test SQLite connection execute SELECT without monitoring"""
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.description = [("id",), ("name",)]
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        conn = SQLiteConnection(mock_conn)

        result = await conn.execute("SELECT * FROM test")

        assert result == mock_cursor
        mock_conn.execute.assert_called_once_with("SELECT * FROM test")

    @pytest.mark.asyncio
    async def test_sqlite_connection_execute_insert_without_monitoring(self):
        """Test SQLite connection execute INSERT without monitoring"""
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.rowcount = 1
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_conn.commit = AsyncMock()

        conn = SQLiteConnection(mock_conn)

        result = await conn.execute("INSERT INTO test VALUES (?, ?)", (1, "test"))

        assert result == 1
        mock_conn.execute.assert_called_once_with(
            "INSERT INTO test VALUES (?, ?)",
            (1, "test"),
        )
        mock_conn.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_sqlite_connection_execute_with_monitoring(self, mock_monitor):
        """Test SQLite connection execute with monitoring"""
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.rowcount = 1
        mock_conn.execute = AsyncMock(return_value=mock_cursor)
        mock_conn.commit = AsyncMock()

        conn = SQLiteConnection(mock_conn, mock_monitor)

        result = await conn.execute("INSERT INTO test VALUES (?, ?)", (1, "test"))

        assert result == 1
        mock_monitor.get_query_monitor.assert_called_once()
        mock_monitor.get_query_monitor().monitor_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_sqlite_connection_execute_error(self):
        """Test SQLite connection execute error"""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(side_effect=aiosqlite.Error("Syntax error"))

        conn = SQLiteConnection(mock_conn)

        with pytest.raises(QueryError) as exc_info:
            await conn.execute("INVALID SQL")

        error = exc_info.value
        assert "Query execution failed" in str(error)
        assert error.details["query"] == "INVALID SQL"
        assert "Syntax error" in error.details["error"]

    @pytest.mark.asyncio
    async def test_sqlite_connection_execute_many(self):
        """Test SQLite connection execute_many"""
        mock_conn = AsyncMock()
        mock_conn.executemany = AsyncMock()
        mock_conn.commit = AsyncMock()

        conn = SQLiteConnection(mock_conn)

        params_list = [(1, "test1"), (2, "test2"), (3, "test3")]
        await conn.execute_many("INSERT INTO test VALUES (?, ?)", params_list)

        mock_conn.executemany.assert_called_once_with(
            "INSERT INTO test VALUES (?, ?)",
            params_list,
        )
        mock_conn.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_sqlite_connection_execute_many_error(self):
        """Test SQLite connection execute_many error"""
        mock_conn = AsyncMock()
        mock_conn.executemany = AsyncMock(
            side_effect=aiosqlite.Error("Constraint violation")
        )

        conn = SQLiteConnection(mock_conn)

        params_list = [(1, "test1"), (2, "test2")]
        with pytest.raises(QueryError) as exc_info:
            await conn.execute_many("INSERT INTO test VALUES (?, ?)", params_list)

        error = exc_info.value
        assert "Batch execution failed" in str(error)
        assert error.details["query"] == "INSERT INTO test VALUES (?, ?)"
        assert "Constraint violation" in error.details["error"]

    @pytest.mark.asyncio
    async def test_sqlite_connection_fetch_one_without_monitoring(self):
        """Test SQLite connection fetch_one without monitoring"""
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=(1, "test"))
        mock_cursor.description = [("id",), ("name",)]
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        conn = SQLiteConnection(mock_conn)

        result = await conn.fetch_one("SELECT * FROM test WHERE id = ?", (1,))

        assert result == {"id": 1, "name": "test"}
        mock_conn.execute.assert_called_once_with(
            "SELECT * FROM test WHERE id = ?",
            (1,),
        )

    @pytest.mark.asyncio
    async def test_sqlite_connection_fetch_one_with_monitoring(self, mock_monitor):
        """Test SQLite connection fetch_one with monitoring"""
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=(1, "test"))
        mock_cursor.description = [("id",), ("name",)]
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        conn = SQLiteConnection(mock_conn, mock_monitor)

        result = await conn.fetch_one("SELECT * FROM test WHERE id = ?", (1,))

        assert result == {"id": 1, "name": "test"}
        mock_monitor.get_query_monitor.assert_called_once()

    @pytest.mark.asyncio
    async def test_sqlite_connection_fetch_one_none_result(self):
        """Test SQLite connection fetch_one with no results"""
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.fetchone = AsyncMock(return_value=None)
        mock_cursor.description = [("id",), ("name",)]
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        conn = SQLiteConnection(mock_conn)

        result = await conn.fetch_one("SELECT * FROM test WHERE id = ?", (999,))

        assert result is None

    @pytest.mark.asyncio
    async def test_sqlite_connection_fetch_one_error(self):
        """Test SQLite connection fetch_one error"""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(
            side_effect=aiosqlite.Error("Table doesn't exist")
        )

        conn = SQLiteConnection(mock_conn)

        with pytest.raises(QueryError) as exc_info:
            await conn.fetch_one("SELECT * FROM nonexistent_table")

        error = exc_info.value
        assert "Query fetch failed" in str(error)
        assert error.details["query"] == "SELECT * FROM nonexistent_table"
        assert "Table doesn't exist" in error.details["error"]

    @pytest.mark.asyncio
    async def test_sqlite_connection_fetch_all_without_monitoring(self):
        """Test SQLite connection fetch_all without monitoring"""
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(
            return_value=[(1, "test1"), (2, "test2"), (3, "test3")],
        )
        mock_cursor.description = [("id",), ("name",)]
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        conn = SQLiteConnection(mock_conn)

        result = await conn.fetch_all("SELECT * FROM test")

        assert len(result) == 3
        assert result[0] == {"id": 1, "name": "test1"}
        assert result[1] == {"id": 2, "name": "test2"}
        assert result[2] == {"id": 3, "name": "test3"}
        mock_conn.execute.assert_called_once_with("SELECT * FROM test")

    @pytest.mark.asyncio
    async def test_sqlite_connection_fetch_all_empty_result(self):
        """Test SQLite connection fetch_all with empty results"""
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=[])
        mock_cursor.description = [("id",), ("name",)]
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        conn = SQLiteConnection(mock_conn)

        result = await conn.fetch_all("SELECT * FROM test WHERE id = ?", (999,))

        assert result == []

    @pytest.mark.asyncio
    async def test_sqlite_connection_fetch_all_with_monitoring(self, mock_monitor):
        """Test SQLite connection fetch_all with monitoring"""
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=[(1, "test1"), (2, "test2")])
        mock_cursor.description = [("id",), ("name",)]
        mock_conn.execute = AsyncMock(return_value=mock_cursor)

        conn = SQLiteConnection(mock_conn, mock_monitor)

        result = await conn.fetch_all("SELECT * FROM test")

        assert len(result) == 2
        mock_monitor.get_query_monitor.assert_called_once()

    @pytest.mark.asyncio
    async def test_sqlite_connection_fetch_all_error(self):
        """Test SQLite connection fetch_all error"""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(side_effect=aiosqlite.Error("Permission denied"))

        conn = SQLiteConnection(mock_conn)

        with pytest.raises(QueryError) as exc_info:
            await conn.fetch_all("SELECT * FROM restricted_table")

        error = exc_info.value
        assert "Query fetch all failed" in str(error)
        assert error.details["query"] == "SELECT * FROM restricted_table"
        assert "Permission denied" in error.details["error"]

    @pytest.mark.asyncio
    async def test_sqlite_connection_close(self):
        """Test SQLite connection close"""
        mock_conn = AsyncMock()
        conn = SQLiteConnection(mock_conn)

        await conn.close()  # Should not raise any errors

    @pytest.mark.asyncio
    async def test_sqlite_pool_get_connection_error(self):
        """Test SQLite pool get_connection error"""
        with patch("lexigram.sql.backends.sqlite.aiosqlite") as mock_aiosqlite:
            mock_conn = AsyncMock()
            mock_aiosqlite.connect = AsyncMock(return_value=mock_conn)

            pool = SQLiteConnectionPool("test.db")
            await pool.initialize()

            # Mock circuit breaker to fail
            mock_circuit_breaker = Mock()

            class MockAsyncContextManager:
                async def __aenter__(self):
                    raise RuntimeError("Circuit breaker open")

                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    pass

            mock_circuit_breaker.protect = Mock(return_value=MockAsyncContextManager())
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
    async def test_sqlite_pool_close(self):
        """Test SQLite pool close"""
        with patch("lexigram.sql.backends.sqlite.aiosqlite") as mock_aiosqlite:
            mock_conn = AsyncMock()
            mock_aiosqlite.connect = AsyncMock(return_value=mock_conn)

            pool = SQLiteConnectionPool("test.db")
            await pool.initialize()

            await pool.shutdown()

            assert pool._conn is None
            assert pool._is_healthy is False
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_sqlite_pool_close_without_initialization(self):
        """Test SQLite pool close without initialization"""
        pool = SQLiteConnectionPool("test.db")

        await pool.shutdown()  # Should not raise any errors

    @pytest.mark.asyncio
    async def test_sqlite_pool_health_check_healthy(self):
        """Test SQLite pool health check when healthy"""
        with patch("lexigram.sql.backends.sqlite.aiosqlite") as mock_aiosqlite:
            mock_conn = AsyncMock()
            mock_cursor = AsyncMock()
            mock_conn.execute = AsyncMock(return_value=mock_cursor)
            mock_aiosqlite.connect = AsyncMock(return_value=mock_conn)

            pool = SQLiteConnectionPool("test.db")
            await pool.initialize()

            # Mock circuit breaker as async context manager
            mock_circuit_breaker = Mock()

            @asynccontextmanager
            async def mock_protect():
                yield

            mock_circuit_breaker.protect = Mock(side_effect=mock_protect)
            pool.circuit_breaker = mock_circuit_breaker

            health = await pool.health_check()

            assert health.status == HealthStatus.HEALTHY
            assert health.details.get("database") == "test.db"
            assert health.details.get("connections_created") == 1
            assert "active_connections" in health.details
            assert "error_count" in health.details

    @pytest.mark.asyncio
    async def test_sqlite_pool_health_check_unhealthy_no_connection(self):
        """Test SQLite pool health check when connection not initialized"""
        pool = SQLiteConnectionPool("test.db")

        health = await pool.health_check()

        assert health.status == HealthStatus.UNHEALTHY
        assert health.message == "Connection not initialized"

    @pytest.mark.asyncio
    async def test_sqlite_pool_health_check_unhealthy_query_failed(self):
        """Test SQLite pool health check when query fails"""
        with patch("lexigram.sql.backends.sqlite.aiosqlite") as mock_aiosqlite:
            mock_conn = AsyncMock()
            mock_aiosqlite.connect = AsyncMock(return_value=mock_conn)

            pool = SQLiteConnectionPool("test.db")
            await pool.initialize()

            # Mock circuit breaker
            mock_circuit_breaker = Mock()

            @asynccontextmanager
            async def mock_protect():
                yield

            mock_circuit_breaker.protect = Mock(side_effect=mock_protect)
            pool.circuit_breaker = mock_circuit_breaker

            # Make execute fail
            pool._conn.execute = AsyncMock(side_effect=OSError("Connection failed"))

            health = await pool.health_check()

            assert health.status == HealthStatus.UNHEALTHY
            assert health.message is not None
            assert health.details.get("error_count") == 1  # Health check error

    @pytest.mark.asyncio
    async def test_sqlite_pool_health_check_caching(self):
        """Test SQLite pool health check caching"""
        with patch("lexigram.sql.backends.sqlite.aiosqlite") as mock_aiosqlite:
            mock_conn = AsyncMock()
            mock_cursor = AsyncMock()
            mock_conn.execute = AsyncMock(return_value=mock_cursor)
            mock_aiosqlite.connect = AsyncMock(return_value=mock_conn)

            pool = SQLiteConnectionPool("test.db")
            await pool.initialize()

            # Mock circuit breaker as async context manager
            mock_circuit_breaker = Mock()

            @asynccontextmanager
            async def mock_protect():
                yield

            mock_circuit_breaker.protect = Mock(side_effect=mock_protect)
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
    async def test_sqlite_pool_get_stats(self):
        """Test SQLite pool statistics"""
        pool = SQLiteConnectionPool("test.db", min_size=5, max_size=25)

        stats = await pool.get_pool_stats()

        assert stats["database"] == "test.db"
        assert stats["is_initialized"] is False
        assert stats["is_healthy"] is False
        assert stats["total_connections_created"] == 0
        assert stats["active_connection_count"] == 0
        assert stats["error_count"] == 0
        assert "circuit_breaker_state" in stats
        assert "last_health_check" in stats

    @pytest.mark.asyncio
    async def test_sqlite_pool_with_monitoring(self, mock_monitor):
        """Test SQLite pool with monitoring enabled"""
        with patch("lexigram.sql.backends.sqlite.aiosqlite") as mock_aiosqlite:
            mock_conn = AsyncMock()
            mock_aiosqlite.connect = AsyncMock(return_value=mock_conn)

            pool = SQLiteConnectionPool("test.db", monitor=mock_monitor)
            await pool.initialize()

            assert pool.monitor == mock_monitor
            mock_monitor.start_pool_monitoring.assert_called_once()

            await pool.shutdown()
            mock_monitor.stop_pool_monitoring.assert_called_once()

    @pytest.mark.asyncio
    async def test_sqlite_pool_retry_logic(self):
        """Test SQLite pool retry logic on initialization failures"""
        with patch("lexigram.sql.backends.sqlite.aiosqlite"):
            # Mock retry_call to track calls
            with patch(
                "lexigram.sql.backends.sqlite.retry_call", new_callable=AsyncMock
            ) as mock_retry:
                mock_conn = AsyncMock()
                mock_retry.return_value = mock_conn

                pool = SQLiteConnectionPool("test.db")
                await pool.initialize()

                # Verify retry_call was called with correct parameters
                mock_retry.assert_called_once()
                call_args = mock_retry.call_args
                assert call_args[0][0] == pool._create_connection  # Function to retry
                assert call_args.kwargs["config"] == pool.retry_config  # Retry config

    @pytest.mark.asyncio
    async def test_sqlite_pool_circuit_breaker(self):
        """Test SQLite pool circuit breaker integration"""
        with patch("lexigram.sql.backends.sqlite.aiosqlite") as mock_aiosqlite:
            mock_conn = AsyncMock()
            mock_aiosqlite.connect = AsyncMock(return_value=mock_conn)

            pool = SQLiteConnectionPool("test.db")
            await pool.initialize()

            # Mock circuit breaker
            mock_circuit_breaker = Mock()

            @asynccontextmanager
            async def mock_protect():
                yield

            mock_circuit_breaker.protect = Mock(side_effect=mock_protect)
            pool.circuit_breaker = mock_circuit_breaker

            async with pool.get_connection():
                pass

            # Verify circuit breaker was used
            mock_circuit_breaker.protect.assert_called_once()

    @pytest.mark.asyncio
    async def test_sqlite_connection_with_custom_monitor(self, mock_monitor):
        """Test SQLite connection with custom monitor"""
        mock_conn = AsyncMock()
        conn = SQLiteConnection(mock_conn, mock_monitor)

        assert conn.monitor == mock_monitor
        assert conn.connection_id.startswith("sqlite_")

    def test_sqlite_import_error_when_unavailable(self):
        """Test SQLite import error when aiosqlite not available"""
        with patch("lexigram.sql.backends.sqlite.HAS_SQLITE", False):
            with pytest.raises(
                ImportError,
                match="aiosqlite is required for SQLite support",
            ):
                SQLiteConnectionPool("test.db")

    @pytest.mark.asyncio
    async def test_sqlite_factory_function(self):
        """Test create_sqlite_pool factory function"""
        mock_monitor = Mock()
        mock_monitor.start_pool_monitoring = AsyncMock()

        pool = create_sqlite_pool(database="production.db", monitor=mock_monitor)

        assert isinstance(pool, SQLiteConnectionPool)
        assert pool.database == "production.db"
        assert pool.monitor == mock_monitor

    @pytest.mark.asyncio
    async def test_sqlite_connection_error_details(self):
        """Test SQLite connection error includes query details"""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(side_effect=aiosqlite.Error("Network timeout"))

        conn = SQLiteConnection(mock_conn)

        with pytest.raises(QueryError) as exc_info:
            await conn.execute("SELECT * FROM large_table", (1, 2, 3))

        error = exc_info.value
        assert "Query execution failed" in str(error)
        assert error.details["query"] == "SELECT * FROM large_table"
        assert "Network timeout" in error.details["error"]

    @pytest.mark.asyncio
    async def test_sqlite_fetch_error_details(self):
        """Test SQLite fetch error includes query details"""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(
            side_effect=aiosqlite.Error("Table doesn't exist")
        )

        conn = SQLiteConnection(mock_conn)

        with pytest.raises(QueryError) as exc_info:
            await conn.fetch_one("SELECT * FROM nonexistent_table", (1,))

        error = exc_info.value
        assert "Query fetch failed" in str(error)
        assert error.details["query"] == "SELECT * FROM nonexistent_table"
        assert "Table doesn't exist" in error.details["error"]

    @pytest.mark.asyncio
    async def test_sqlite_execute_many_error_details(self):
        """Test SQLite execute_many error includes query details"""
        mock_conn = AsyncMock()
        mock_conn.executemany = AsyncMock(side_effect=aiosqlite.Error("Duplicate key"))

        conn = SQLiteConnection(mock_conn)

        params_list = [("value1",), ("value2",)]
        with pytest.raises(QueryError) as exc_info:
            await conn.execute_many("INSERT INTO unique_table VALUES (?)", params_list)

        error = exc_info.value
        assert "Batch execution failed" in str(error)
        assert error.details["query"] == "INSERT INTO unique_table VALUES (?)"
        assert "Duplicate key" in error.details["error"]
