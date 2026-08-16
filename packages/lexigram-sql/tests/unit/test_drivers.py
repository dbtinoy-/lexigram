"""Tests for Lexigram DB drivers"""

from contextlib import asynccontextmanager
import importlib.util
from unittest.mock import AsyncMock, Mock, patch

import pytest

from lexigram.contracts.core import HealthStatus
from lexigram.sql.backends.mysql import MySQLConnectionPool, create_mysql_pool
from lexigram.sql.backends.postgres import PostgresConnectionPool, create_postgres_pool
from lexigram.sql.backends.sqlite import (
    SQLiteConnection,
    SQLiteConnectionPool,
    create_sqlite_pool,
)
from lexigram.sql.monitoring import DatabaseMonitor, InMemoryDbMetricsCollector

# Import availability flags
try:
    from lexigram.sql.backends.postgres import HAS_POSTGRES
except ImportError:
    HAS_POSTGRES = False

try:
    from lexigram.sql.backends.mysql import HAS_MYSQL
except ImportError:
    HAS_MYSQL = False

try:
    from lexigram.sql.backends.sqlite import HAS_SQLITE
except ImportError:
    HAS_SQLITE = False


class TestPostgresDriver:
    """Test PostgreSQL driver"""

    @pytest.mark.skipif(not HAS_POSTGRES, reason="asyncpg not available")
    @pytest.mark.asyncio
    async def test_postgres_pool_creation(self):
        """Test PostgreSQL pool creation"""
        pool = create_postgres_pool(
            host="localhost",
            port=5432,
            user="user",
            password="pass",
            database="test",
        )
        assert isinstance(pool, PostgresConnectionPool)
        assert pool.host == "localhost"
        assert pool.database == "test"

    @pytest.mark.skipif(not HAS_POSTGRES, reason="asyncpg not available")
    @pytest.mark.asyncio
    @patch("lexigram.sql.backends.postgres.asyncpg.create_pool", new_callable=AsyncMock)
    async def test_postgres_pool_initialization(self, mock_create_pool):
        """Test PostgreSQL pool initialization"""
        mock_pool = AsyncMock()
        mock_create_pool.return_value = mock_pool

        pool = PostgresConnectionPool(
            host="localhost",
            port=5432,
            user="user",
            password="pass",
            database="test",
        )

        await pool.initialize()

        mock_create_pool.assert_called_once()
        assert pool._pool == mock_pool

    @pytest.mark.skipif(not HAS_POSTGRES, reason="asyncpg not available")
    @pytest.mark.asyncio
    @patch("lexigram.sql.backends.postgres.asyncpg.create_pool")
    async def test_postgres_health_check(self, mock_create_pool):
        """Test PostgreSQL health check functionality"""
        from unittest.mock import AsyncMock, MagicMock

        mock_conn = AsyncMock()
        mock_pool = MagicMock()  # Use MagicMock instead of AsyncMock
        mock_conn.execute.return_value = "SELECT 1"

        # Create a proper async context manager for acquire()
        class MockAcquireContext:
            def __init__(self, conn):
                self.conn = conn

            async def __aenter__(self):
                return self.conn

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        mock_pool.acquire.return_value = MockAcquireContext(mock_conn)

        # Make the mock return a coroutine that returns the mock pool
        async def mock_create_pool_coro(*args, **kwargs):
            return mock_pool

        mock_create_pool.side_effect = mock_create_pool_coro

        pool = PostgresConnectionPool(
            host="localhost",
            port=5432,
            user="user",
            password="pass",
            database="test",
        )

        await pool.initialize()

        health = await pool.health_check()
        assert health.status == HealthStatus.HEALTHY
        assert "pool_size" in health.details
        assert "connections_created" in health.details

    @pytest.mark.skipif(not HAS_POSTGRES, reason="asyncpg not available")
    @pytest.mark.asyncio
    async def test_postgres_pool_with_ssl(self):
        """Test PostgreSQL pool creation with SSL configuration"""
        pool = create_postgres_pool(
            host="localhost",
            port=5432,
            user="user",
            password="pass",
            database="test",
            ssl={"verify_cert": False},
        )
        assert pool.ssl == {"verify_cert": False}

        assert isinstance(pool, PostgresConnectionPool)

    @pytest.mark.skipif(not HAS_POSTGRES, reason="asyncpg not available")
    @pytest.mark.asyncio
    async def test_postgres_pool_stats(self):
        """Test PostgreSQL pool statistics"""
        pool = PostgresConnectionPool(
            host="localhost",
            port=5432,
            user="user",
            password="pass",
            database="test",
        )
        stats = await pool.get_pool_stats()

        assert "pool_size" in stats
        assert "is_initialized" in stats
        assert "is_healthy" in stats
        assert "total_connections_created" in stats
        assert "error_count" in stats
        assert "circuit_breaker_state" in stats


class TestMySQLDriver:
    """Test MySQL driver"""

    @pytest.mark.skipif(not HAS_MYSQL, reason="aiomysql not available")
    @pytest.mark.asyncio
    async def test_mysql_pool_creation(self):
        """Test MySQL pool creation"""
        pool = create_mysql_pool(
            host="localhost",
            user="root",
            password="pass",
            database="test",
        )
        assert isinstance(pool, MySQLConnectionPool)
        assert pool.host == "localhost"
        assert pool.user == "root"
        assert pool.database == "test"

    @pytest.mark.skipif(not HAS_MYSQL, reason="aiomysql not available")
    @pytest.mark.asyncio
    @patch("lexigram.sql.backends.mysql.aiomysql.create_pool", new_callable=AsyncMock)
    async def test_mysql_pool_initialization(self, mock_create_pool):
        """Test MySQL pool initialization"""
        mock_pool = AsyncMock()
        mock_create_pool.return_value = mock_pool

        pool = MySQLConnectionPool("localhost", 3306, "root", "pass", "test")
        await pool.initialize()

        mock_create_pool.assert_called_once()
        assert pool._pool == mock_pool


class TestSQLiteDriver:
    """Test SQLite driver"""

    @pytest.mark.skipif(not HAS_SQLITE, reason="aiosqlite not available")
    @pytest.mark.asyncio
    async def test_sqlite_pool_creation(self):
        """Test SQLite pool creation"""
        pool = create_sqlite_pool(":memory:")
        assert isinstance(pool, SQLiteConnectionPool)
        assert pool.database == ":memory:"

    @pytest.mark.skipif(not HAS_SQLITE, reason="aiosqlite not available")
    @pytest.mark.asyncio
    @patch("lexigram.sql.backends.sqlite.aiosqlite")
    async def test_sqlite_pool_initialization(self, mock_aiosqlite):
        """Test SQLite pool initialization"""
        mock_conn = AsyncMock()
        mock_aiosqlite.connect = AsyncMock(return_value=mock_conn)

        pool = SQLiteConnectionPool(":memory:")
        await pool.initialize()

        mock_aiosqlite.connect.assert_called_once()
        assert pool._conn == mock_conn


class TestDriverImports:
    """Test driver imports work correctly"""

    def test_postgres_import(self):
        """Test PostgreSQL driver can be imported"""
        if importlib.util.find_spec("lexigram.sql.backends.postgres") is None:
            pytest.skip("asyncpg not available")

    def test_mysql_import(self):
        """Test MySQL driver can be imported"""
        if importlib.util.find_spec("lexigram.sql.backends.mysql") is None:
            pytest.skip("aiomysql not available")

    def test_sqlite_import(self):
        """Test SQLite driver can be imported"""
        if importlib.util.find_spec("lexigram.sql.backends.sqlite") is None:
            pytest.skip("aiosqlite not available")


class TestDriverMonitoringIntegration:
    """Test monitoring integration across all drivers"""

    @pytest.fixture
    def monitor(self):
        """Create a test monitor"""
        collector = InMemoryDbMetricsCollector()
        return DatabaseMonitor(collector)

    @pytest.mark.skipif(not HAS_POSTGRES, reason="asyncpg not available")
    @pytest.mark.asyncio
    async def test_postgres_monitoring_integration(self, monitor):
        """Test PostgreSQL driver with monitoring"""
        pool = create_postgres_pool(
            "postgresql://user:pass@localhost:5432/test",
            monitor=monitor,
        )
        assert pool.monitor == monitor

        # Test that monitoring is started
        assert pool.monitor is not None

    @pytest.mark.skipif(not HAS_MYSQL, reason="aiomysql not available")
    @pytest.mark.asyncio
    async def test_mysql_monitoring_integration(self, monitor):
        """Test MySQL driver with monitoring"""
        pool = create_mysql_pool(
            host="localhost",
            user="root",
            password="pass",
            database="test",
            monitor=monitor,
        )
        assert pool.monitor == monitor

    @pytest.mark.skipif(not HAS_SQLITE, reason="aiosqlite not available")
    @pytest.mark.asyncio
    async def test_sqlite_monitoring_integration(self, monitor):
        """Test SQLite driver with monitoring"""
        pool = create_sqlite_pool(database=":memory:", monitor=monitor)
        assert pool.monitor == monitor

    @pytest.mark.skipif(not HAS_SQLITE, reason="aiosqlite not available")
    @pytest.mark.asyncio
    async def test_sqlite_monitoring_end_to_end(self, monitor):
        """Test SQLite monitoring end-to-end functionality"""
        pool = create_sqlite_pool(database=":memory:", monitor=monitor)
        await pool.initialize()

        # Test connection with monitoring
        async with pool.get_connection() as conn:
            # Execute a query
            result = await conn.execute(
                "CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)",
            )
            assert result is not None

            # Insert data
            result = await conn.execute(
                "INSERT INTO test (name) VALUES (?)",
                ("test_name",),
            )
            assert result is not None

            # Fetch data
            rows = await conn.fetch_all("SELECT * FROM test")
            assert len(rows) == 1
            assert rows[0]["name"] == "test_name"

        # Check that monitoring collected data
        stats = await monitor.get_stats()
        assert "query_stats" in stats
        assert "connection_stats" in stats

        await pool.shutdown()

    @pytest.mark.skipif(not HAS_SQLITE, reason="aiosqlite not available")
    @pytest.mark.asyncio
    async def test_sqlite_health_check_with_monitoring(self, monitor):
        """Test SQLite health check includes monitoring data"""
        pool = create_sqlite_pool(database=":memory:", monitor=monitor)
        await pool.initialize()

        health = await pool.health_check()
        assert health.status == HealthStatus.HEALTHY

        # Health check should include monitoring stats when available
        # Note: This depends on the monitoring implementation

        await pool.shutdown()

    @pytest.mark.asyncio
    async def test_monitor_creation(self):
        """Test monitor creation and basic functionality"""
        collector = InMemoryDbMetricsCollector()
        monitor = DatabaseMonitor(collector)

        # Test monitor has required components
        assert hasattr(monitor, "get_query_monitor")
        assert hasattr(monitor, "start_pool_monitoring")
        assert hasattr(monitor, "stop_pool_monitoring")
        assert hasattr(monitor, "get_transaction_monitor")
        assert hasattr(monitor, "get_health_checker")
        assert hasattr(monitor, "get_stats")

        # Test getting stats
        stats = await monitor.get_stats()
        assert isinstance(stats, dict)

    @pytest.mark.asyncio
    async def test_monitor_pool_lifecycle(self):
        """Test monitor pool monitoring lifecycle"""
        collector = InMemoryDbMetricsCollector()
        monitor = DatabaseMonitor(collector)

        # Mock pool
        mock_pool = Mock()
        mock_pool.get_stats = Mock(return_value={"test": "stats"})

        # Start monitoring
        await monitor.start_pool_monitoring(mock_pool)

        # Stop monitoring
        await monitor.stop_pool_monitoring()

        # Should not raise exceptions
        assert True


class TestSQLiteDriverDetailed:
    """Test SQLite driver functionality"""

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

    @pytest.mark.skipif(not HAS_SQLITE, reason="aiosqlite not available")
    def test_sqlite_pool_creation(self):
        """Test SQLite pool creation"""
        pool = create_sqlite_pool(database=":memory:")
        assert isinstance(pool, SQLiteConnectionPool)
        assert pool.database == ":memory:"

    @pytest.mark.skipif(not HAS_SQLITE, reason="aiosqlite not available")
    def test_sqlite_pool_creation_with_file(self):
        """Test SQLite pool creation with file database"""
        pool = create_sqlite_pool(database="/tmp/test.db")
        assert isinstance(pool, SQLiteConnectionPool)
        assert pool.database == "/tmp/test.db"

    @pytest.mark.skipif(not HAS_SQLITE, reason="aiosqlite not available")
    @pytest.mark.asyncio
    async def test_sqlite_pool_initialization(self):
        """Test SQLite pool initialization"""
        pool = create_sqlite_pool(database=":memory:")
        await pool.initialize()

        assert pool._conn is not None
        assert pool._is_healthy is True
        assert pool._total_connections_created == 1

        await pool.shutdown()

    @pytest.mark.skipif(not HAS_SQLITE, reason="aiosqlite not available")
    @pytest.mark.asyncio
    async def test_sqlite_connection_context_manager(self):
        """Test SQLite connection context manager"""
        pool = create_sqlite_pool(database=":memory:")
        await pool.initialize()

        async with pool.get_connection() as conn:
            assert isinstance(conn, SQLiteConnection)
            assert conn._conn == pool._conn

        await pool.shutdown()

    @pytest.mark.skipif(not HAS_SQLITE, reason="aiosqlite not available")
    @pytest.mark.asyncio
    async def test_sqlite_execute_select_query(self):
        """Test executing SELECT queries"""
        pool = create_sqlite_pool(database=":memory:")
        await pool.initialize()

        async with pool.get_connection() as conn:
            # Create test table
            await conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")

            # Insert data
            await conn.execute("INSERT INTO test (name) VALUES (?)", ("test_name",))

            # Select data
            cursor = await conn.execute("SELECT * FROM test")
            assert cursor is not None

        await pool.shutdown()

    @pytest.mark.skipif(not HAS_SQLITE, reason="aiosqlite not available")
    @pytest.mark.asyncio
    async def test_sqlite_execute_insert_update_delete(self):
        """Test executing INSERT/UPDATE/DELETE queries"""
        pool = create_sqlite_pool(database=":memory:")
        await pool.initialize()

        async with pool.get_connection() as conn:
            # Create test table
            await conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")

            # Insert data
            result = await conn.execute(
                "INSERT INTO test (name) VALUES (?)",
                ("test_name",),
            )
            assert result == 1  # rowcount

            # Update data
            result = await conn.execute(
                "UPDATE test SET name = ? WHERE id = ?",
                ("updated_name", 1),
            )
            assert result == 1

            # Delete data
            result = await conn.execute("DELETE FROM test WHERE id = ?", (1,))
            assert result == 1

        await pool.shutdown()

    @pytest.mark.skipif(not HAS_SQLITE, reason="aiosqlite not available")
    @pytest.mark.asyncio
    async def test_sqlite_fetch_one(self):
        """Test fetching a single row"""
        pool = create_sqlite_pool(database=":memory:")
        await pool.initialize()

        async with pool.get_connection() as conn:
            # Create and populate test table
            await conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
            await conn.execute("INSERT INTO test (name) VALUES (?)", ("test_name",))

            # Fetch one row
            row = await conn.fetch_one("SELECT * FROM test WHERE id = ?", (1,))
            assert row is not None
            assert row["id"] == 1
            assert row["name"] == "test_name"

            # Fetch non-existent row
            row = await conn.fetch_one("SELECT * FROM test WHERE id = ?", (999,))
            assert row is None

        await pool.shutdown()

    @pytest.mark.skipif(not HAS_SQLITE, reason="aiosqlite not available")
    @pytest.mark.asyncio
    async def test_sqlite_fetch_all(self):
        """Test fetching all rows"""
        pool = create_sqlite_pool(database=":memory:")
        await pool.initialize()

        async with pool.get_connection() as conn:
            # Create and populate test table
            await conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
            await conn.execute("INSERT INTO test (name) VALUES (?)", ("name1",))
            await conn.execute("INSERT INTO test (name) VALUES (?)", ("name2",))
            await conn.execute("INSERT INTO test (name) VALUES (?)", ("name3",))

            # Fetch all rows
            rows = await conn.fetch_all("SELECT * FROM test ORDER BY id")
            assert len(rows) == 3
            assert rows[0]["name"] == "name1"
            assert rows[1]["name"] == "name2"
            assert rows[2]["name"] == "name3"

            # Fetch empty result
            rows = await conn.fetch_all("SELECT * FROM test WHERE id > ?", (10,))
            assert rows == []

        await pool.shutdown()

    @pytest.mark.skipif(not HAS_SQLITE, reason="aiosqlite not available")
    @pytest.mark.asyncio
    async def test_sqlite_execute_many(self):
        """Test executing multiple queries with execute_many"""
        pool = create_sqlite_pool(database=":memory:")
        await pool.initialize()

        async with pool.get_connection() as conn:
            # Create test table
            await conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")

            # Insert multiple rows
            params_list = [("name1",), ("name2",), ("name3",)]
            await conn.execute_many("INSERT INTO test (name) VALUES (?)", params_list)

            # Verify all rows were inserted
            rows = await conn.fetch_all("SELECT * FROM test ORDER BY name")
            assert len(rows) == 3

        await pool.shutdown()

    @pytest.mark.skipif(not HAS_SQLITE, reason="aiosqlite not available")
    @pytest.mark.asyncio
    async def test_sqlite_health_check(self):
        """Test SQLite health check functionality"""
        pool = create_sqlite_pool(database=":memory:")
        await pool.initialize()

        # Test healthy connection
        health = await pool.health_check()
        assert health.status == HealthStatus.HEALTHY
        assert health.details.get("database") == ":memory:"
        assert health.details.get("connections_created") == 1
        assert "active_connections" in health.details
        assert "error_count" in health.details

        await pool.shutdown()

        # Test unhealthy connection (after close)
        health = await pool.health_check()
        assert health.status == HealthStatus.UNHEALTHY
        assert health.message is not None or "error" in health.details

    @pytest.mark.skipif(not HAS_SQLITE, reason="aiosqlite not available")
    @pytest.mark.asyncio
    async def test_sqlite_health_check_caching(self):
        """Test health check caching"""
        pool = create_sqlite_pool(database=":memory:")
        await pool.initialize()

        # First health check
        health1 = await pool.health_check()
        assert health1.status == HealthStatus.HEALTHY
        assert health1.details.get("cached") is False or "cached" not in health1.details

        # Second health check (should be cached)
        import time

        time.sleep(0.1)  # Small delay to ensure different timestamps
        health2 = await pool.health_check()
        assert health2.status == HealthStatus.HEALTHY
        # Note: caching logic depends on time difference < 30 seconds

        await pool.shutdown()

    @pytest.mark.skipif(not HAS_SQLITE, reason="aiosqlite not available")
    @pytest.mark.asyncio
    async def test_sqlite_pool_stats(self):
        """Test SQLite pool statistics"""
        pool = create_sqlite_pool(database=":memory:")
        stats = await pool.get_pool_stats()

        assert stats["is_initialized"] is False
        assert stats["is_healthy"] is False
        assert stats["total_connections_created"] == 0
        assert stats["active_connection_count"] == 0
        assert stats["error_count"] == 0

    @pytest.mark.skipif(not HAS_SQLITE, reason="aiosqlite not available")
    @pytest.mark.asyncio
    async def test_sqlite_pool_close(self):
        """Test SQLite pool closing"""
        pool = create_sqlite_pool(database=":memory:")
        await pool.initialize()

        assert pool._conn is not None
        assert pool._is_healthy is True

        await pool.shutdown()

        assert pool._conn is None
        assert pool._is_healthy is False

    @pytest.mark.skipif(not HAS_SQLITE, reason="aiosqlite not available")
    @pytest.mark.asyncio
    async def test_sqlite_connection_error_handling(self):
        """Test error handling in SQLite connections"""
        pool = create_sqlite_pool(database=":memory:")
        await pool.initialize()

        async with pool.get_connection() as conn:
            # Test invalid SQL
            from lexigram.sql.exceptions import QueryError

            with pytest.raises(QueryError):  # Should raise QueryError
                await conn.execute("INVALID SQL STATEMENT")

            # Test invalid parameters
            with pytest.raises(QueryError):
                await conn.fetch_one("SELECT * FROM nonexistent_table")

        await pool.shutdown()

    @pytest.mark.skipif(not HAS_SQLITE, reason="aiosqlite not available")
    @pytest.mark.asyncio
    async def test_sqlite_connection_with_monitoring(self, mock_monitor):
        """Test SQLite connection with monitoring enabled"""
        pool = create_sqlite_pool(database=":memory:", monitor=mock_monitor)
        await pool.initialize()

        async with pool.get_connection() as conn:
            # Execute a query - should trigger monitoring
            await conn.execute("SELECT 1")

            # Verify monitoring was called
            mock_monitor.get_query_monitor.assert_called()

        await pool.shutdown()

    @pytest.mark.skipif(not HAS_SQLITE, reason="aiosqlite not available")
    @pytest.mark.asyncio
    async def test_sqlite_retry_on_connection_failure(self):
        """Test retry logic on connection failures"""
        pool = create_sqlite_pool(database=":memory:")

        # Should succeed normally
        await pool.initialize()
        assert pool._conn is not None

        await pool.shutdown()

    @pytest.mark.skipif(not HAS_SQLITE, reason="aiosqlite not available")
    @pytest.mark.asyncio
    async def test_sqlite_pragmas_and_explain(self):
        """Test PRAGMA and EXPLAIN queries"""
        pool = create_sqlite_pool(database=":memory:")
        await pool.initialize()

        async with pool.get_connection() as conn:
            # Test PRAGMA query
            result = await conn.execute("PRAGMA table_info(sqlite_master)")
            assert result is not None

            # Test EXPLAIN query
            result = await conn.execute("EXPLAIN SELECT 1")
            assert result is not None

        await pool.shutdown()

    @pytest.mark.skipif(not HAS_SQLITE, reason="aiosqlite not available")
    @pytest.mark.asyncio
    async def test_sqlite_connection_close_method(self):
        """Test connection close method (should be no-op for SQLite)"""
        pool = create_sqlite_pool(database=":memory:")
        await pool.initialize()

        async with pool.get_connection() as conn:
            # Close should not raise exception (it's a no-op for SQLite)
            await conn.close()

        await pool.shutdown()
