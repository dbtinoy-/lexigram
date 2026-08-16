"""Unit tests for BaseDatabaseProvider"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from lexigram.contracts.data import (
    ConnectionPoolProtocol,
    DeleteResult,
    InsertResult,
    QueryLoggerProtocol,
    QueryResult,
    UpdateResult,
)
from lexigram.contracts.core import HealthStatus
from lexigram.sql.providers.base_provider import DatabaseDriver


class ConcreteDatabaseProvider(DatabaseDriver):
    """Concrete implementation for testing"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._connections_created = []
        self._connections_closed = []

    async def _create_connection(self):
        conn = Mock()
        self._connections_created.append(conn)
        return conn

    async def _close_connection(self, connection):
        self._connections_closed.append(connection)

    async def _execute_query_raw(
        self, connection, sql: str, params: list[Any] | None = None,
    ) -> list[dict[str, Any]]:
        if "SELECT 1" in sql:
            return [{"health_check": 1}]
        elif "sqlite_master" in sql:
            return [{"name": "test_table"}]
        elif "PRAGMA table_info" in sql:
            return [
                {
                    "name": "id",
                    "type": "INTEGER",
                    "notnull": 1,
                    "dflt_value": None,
                    "pk": 1,
                },
                {
                    "name": "name",
                    "type": "VARCHAR",
                    "notnull": 0,
                    "dflt_value": None,
                    "pk": 0,
                },
            ]
        return []

    async def _execute_modify_raw(
        self, connection, sql: str, params: list[Any] | None = None,
    ) -> int:
        return 1

    async def _begin_transaction_raw(self, connection, isolation=None):
        pass

    async def _commit_transaction_raw(self, connection):
        pass

    async def _rollback_transaction_raw(self, connection):
        pass

    async def _get_last_insert_id(self, connection, table: str) -> Any | None:
        return 123


class TestBaseDatabaseProvider:
    """Test BaseDatabaseProvider functionality"""

    @pytest.fixture
    def mock_connection_pool(self):
        """Create a mock connection pool"""
        pool = Mock(spec=ConnectionPoolProtocol)
        pool.initialize = AsyncMock()
        pool.shutdown = AsyncMock()
        pool.get_connection = MagicMock()
        pool.get_connection.return_value.__aenter__ = AsyncMock(return_value=Mock())
        pool.get_connection.return_value.__aexit__ = AsyncMock(return_value=None)
        return pool

    @pytest.fixture
    def mock_query_logger(self):
        """Create a mock query logger"""
        logger = Mock(spec=QueryLoggerProtocol)
        logger.log_query = AsyncMock()
        return logger

    @pytest.mark.asyncio
    async def test_init_basic_connection_string(self):
        """Test initialization with basic connection string"""
        provider = ConcreteDatabaseProvider("sqlite:///test.db")

        assert provider.connection_manager.connection_string == "sqlite:///test.db"
        assert provider.database_type == "sqlite"
        assert provider.connection_manager.database == "test.db"
        assert provider.connection_manager.host is None
        assert provider.connection_manager.port is None
        assert provider.connection_manager.username is None
        assert provider.connection_manager.password is None
        assert provider.connection_pool is None
        assert provider.query_executor.query_logger is None
        assert await provider.is_connected() is False

    @pytest.mark.asyncio
    async def test_init_complex_connection_string(self):
        """Test initialization with complex connection string"""
        provider = ConcreteDatabaseProvider(
            "postgresql://user:pass@localhost:5432/mydb",
        )

        assert provider.database_type == "postgresql"
        assert provider.connection_manager.host == "localhost"
        assert provider.connection_manager.port == 5432
        assert provider.connection_manager.database == "mydb"
        assert provider.connection_manager.username == "user"
        assert provider.connection_manager.password == "pass"

    @pytest.mark.asyncio
    async def test_init_with_connection_pool(self, mock_connection_pool):
        """Test initialization with connection pool"""
        provider = ConcreteDatabaseProvider(
            "sqlite:///test.db", connection_pool=mock_connection_pool,
        )

        assert provider.connection_pool == mock_connection_pool

    @pytest.mark.asyncio
    async def test_init_with_query_logger(self, mock_query_logger):
        """Test initialization with query logger"""
        provider = ConcreteDatabaseProvider(
            "sqlite:///test.db", query_logger=mock_query_logger,
        )

        assert provider.query_executor.query_logger == mock_query_logger

    @pytest.mark.asyncio
    async def test_connect_without_pool(self):
        """Test connecting without connection pool"""
        provider = ConcreteDatabaseProvider("sqlite:///test.db")

        await provider.connect()

        assert await provider.is_connected() is True
        assert len(provider._connections_created) == 1

    @pytest.mark.asyncio
    async def test_connect_with_pool(self, mock_connection_pool):
        """Test connecting with connection pool"""
        provider = ConcreteDatabaseProvider(
            "sqlite:///test.db", connection_pool=mock_connection_pool,
        )

        await provider.connect()

        mock_connection_pool.initialize.assert_called_once()
        assert await provider.is_connected() is True

    @pytest.mark.asyncio
    async def test_disconnect_without_pool(self):
        """Test disconnecting without connection pool"""
        provider = ConcreteDatabaseProvider("sqlite:///test.db")
        await provider.connect()

        await provider.disconnect()

        assert await provider.is_connected() is False
        assert len(provider._connections_closed) == 1

    @pytest.mark.asyncio
    async def test_disconnect_with_pool(self, mock_connection_pool):
        """Test disconnecting with connection pool"""
        provider = ConcreteDatabaseProvider(
            "sqlite:///test.db", connection_pool=mock_connection_pool,
        )
        await provider.connect()

        await provider.disconnect()

        mock_connection_pool.shutdown.assert_called_once()
        assert await provider.is_connected() is False

    @pytest.mark.asyncio
    async def test_is_connected(self):
        """Test is_connected method"""
        provider = ConcreteDatabaseProvider("sqlite:///test.db")

        assert await provider.is_connected() is False

        await provider.connect()
        assert await provider.is_connected() is True

        await provider.disconnect()
        assert await provider.is_connected() is False

    @pytest.mark.asyncio
    async def test_execute_query_success(self):
        """Test successful query execution"""
        provider = ConcreteDatabaseProvider("sqlite:///test.db")
        await provider.connect()

        result = await provider.execute_query("SELECT * FROM test_table", ["param1"])

        assert isinstance(result, QueryResult)
        assert result.success is True
        assert result.execution_time >= 0
        assert result.error_message is None

    @pytest.mark.asyncio
    async def test_execute_query_with_exception(self):
        """Test query execution with exception"""
        provider = ConcreteDatabaseProvider("sqlite:///test.db")
        await provider.connect()

        # Mock the _execute_query_raw to raise exception
        original_method = provider._execute_query_raw

        async def failing_query(*args, **kwargs):
            raise RuntimeError("Query failed")

        provider._execute_query_raw = failing_query

        with pytest.raises(RuntimeError, match="Query failed"):
            await provider.execute_query("SELECT * FROM test_table")

        # Restore original method
        provider._execute_query_raw = original_method

    @pytest.mark.asyncio
    async def test_execute_insert_success(self):
        """Test successful insert execution"""
        provider = ConcreteDatabaseProvider("sqlite:///test.db")
        await provider.connect()

        result = await provider.execute_insert(
            "test_table", {"name": "test", "value": 42},
        )

        assert isinstance(result, InsertResult)
        assert result.affected_rows == 1
        assert result.inserted_id == 123
        assert result.execution_time >= 0
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_update_success(self):
        """Test successful update execution"""
        provider = ConcreteDatabaseProvider("sqlite:///test.db")
        await provider.connect()

        result = await provider.execute_update(
            "test_table", {"name": "updated"}, "id = ?", [1],
        )

        assert isinstance(result, UpdateResult)
        assert result.affected_rows == 1
        assert result.execution_time >= 0
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_delete_success(self):
        """Test successful delete execution"""
        provider = ConcreteDatabaseProvider("sqlite:///test.db")
        await provider.connect()

        result = await provider.execute_delete("test_table", "id = ?", [1])

        assert isinstance(result, DeleteResult)
        assert result.affected_rows == 1
        assert result.execution_time >= 0
        assert result.success is True

    @pytest.mark.asyncio
    async def test_transaction_context_manager_success(self):
        """Test transaction context manager with success"""
        provider = ConcreteDatabaseProvider("sqlite:///test.db")
        await provider.connect()

        async with provider.transaction():
            # Transaction should be active here
            assert provider.transaction_manager.in_transaction is True
            assert provider.transaction_manager._transaction_connection is not None

        # Transaction should be committed and cleaned up
        assert provider.transaction_manager.in_transaction is False
        assert provider.transaction_manager._transaction_connection is None

    @pytest.mark.asyncio
    async def test_transaction_context_manager_exception(self):
        """Test transaction context manager with exception (rollback)"""
        provider = ConcreteDatabaseProvider("sqlite:///test.db")
        await provider.connect()

        with pytest.raises(ValueError):
            async with provider.transaction():
                assert provider.transaction_manager.in_transaction is True
                raise ValueError("Test exception")

        # Transaction should be rolled back and cleaned up
        assert provider.transaction_manager.in_transaction is False
        assert provider.transaction_manager._transaction_connection is None

    @pytest.mark.asyncio
    async def test_nested_transaction(self):
        """Test nested transactions"""
        provider = ConcreteDatabaseProvider("sqlite:///test.db")
        await provider.connect()

        async with provider.transaction():
            assert provider.transaction_manager.in_transaction is True

            # Nested transaction should just yield without creating new transaction
            async with provider.transaction():
                assert provider.transaction_manager.in_transaction is True

            assert provider.transaction_manager.in_transaction is True

        assert provider.transaction_manager.in_transaction is False

    @pytest.mark.asyncio
    async def test_manual_transaction_methods(self):
        """Test manual transaction begin/commit/rollback"""
        provider = ConcreteDatabaseProvider("sqlite:///test.db")

        # Begin transaction
        await provider.begin_transaction()
        assert provider.transaction_manager.in_transaction is True
        assert provider.transaction_manager._transaction_connection is not None

        # Commit transaction
        await provider.commit_transaction()
        assert provider.transaction_manager.in_transaction is False
        assert provider.transaction_manager._transaction_connection is None

        await provider.begin_transaction()
        await provider.rollback_transaction()
        assert provider.transaction_manager.in_transaction is False
        assert provider.transaction_manager._transaction_connection is None

    @pytest.mark.asyncio
    async def test_table_exists_sqlite_syntax(self):
        """Test table_exists with SQLite syntax"""
        provider = ConcreteDatabaseProvider("sqlite:///test.db")
        await provider.connect()

        exists = await provider.table_exists("test_table")
        assert exists is True

    @pytest.mark.asyncio
    async def test_table_exists_fallback(self):
        """Test table_exists fallback for other databases"""
        provider = ConcreteDatabaseProvider("postgresql://user:pass@localhost/mydb")
        await provider.connect()

        # Mock execute_query to simulate table exists via SELECT
        original_execute_query = provider.execute_query

        async def mock_execute_query(sql, params=None):
            if "SELECT 1 FROM test_table" in sql:
                return QueryResult(
                    rows=[{"col": 1}], row_count=1, execution_time=0.01, success=True,
                )
            return await original_execute_query(sql, params)

        provider.execute_query = mock_execute_query

        exists = await provider.table_exists("test_table")
        assert exists is True

    @pytest.mark.asyncio
    async def test_get_table_columns(self):
        """Test get_table_columns"""
        provider = ConcreteDatabaseProvider("sqlite:///test.db")
        await provider.connect()

        columns = await provider.get_table_columns("test_table")

        assert len(columns) == 2
        assert columns[0]["name"] == "id"
        assert columns[0]["type"] == "INTEGER"
        assert columns[0]["nullable"] is False
        assert columns[0]["primary_key"] is True
        assert columns[1]["name"] == "name"
        assert columns[1]["type"] == "VARCHAR"
        assert columns[1]["nullable"] is True
        assert columns[1]["primary_key"] is False

    @pytest.mark.asyncio
    async def test_create_table(self):
        """Test create_table"""
        provider = ConcreteDatabaseProvider("sqlite:///test.db")
        await provider.connect()

        await provider.create_table(
            "test_table",
            {"id": "INTEGER", "name": "VARCHAR(100)", "user_id": "INTEGER"},
        )

        # Should not raise exception
        assert True

    @pytest.mark.asyncio
    async def test_drop_table(self):
        """Test drop_table"""
        provider = ConcreteDatabaseProvider("sqlite:///test.db")
        await provider.connect()

        await provider.drop_table("test_table")

        # Should not raise exception
        assert True

    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        """Test health check when healthy"""
        provider = ConcreteDatabaseProvider("sqlite:///test.db")
        await provider.connect()

        health = await provider.health_check()

        assert health.status == HealthStatus.HEALTHY
        assert "message" in health.details
        assert health.details["message"] == "Database connection successful"
        assert health.duration_ms is not None
        assert health.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self):
        """Test health check when unhealthy"""
        provider = ConcreteDatabaseProvider("sqlite:///test.db")
        await provider.connect()

        # Mock _execute_query_raw to raise exception
        original_execute_query_raw = provider._execute_query_raw

        async def failing_query(*args, **kwargs):
            raise RuntimeError("Connection failed")

        provider._execute_query_raw = failing_query

        health = await provider.health_check()

        assert health.status == HealthStatus.UNHEALTHY
        assert "Database connection failed: Connection failed" in health.error
        assert health.details["database_type"] == "sqlite"

        # Restore original method
        provider._execute_query_raw = original_execute_query_raw

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Test get_stats method"""
        provider = ConcreteDatabaseProvider("sqlite:///test.db")

        stats = await provider.get_stats()

        assert stats["database_type"] == "sqlite"
        assert stats["connected"] is False
        assert stats["connection_pool"] is False
        assert stats["query_logger"] is False

        # Test with connection and pool
        mock_pool = Mock()
        mock_pool.initialize = AsyncMock()
        mock_pool.shutdown = AsyncMock()
        mock_pool.get_connection = MagicMock()
        mock_pool.get_connection.return_value.__aenter__ = AsyncMock(return_value=Mock())
        mock_pool.get_connection.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_logger = Mock()
        provider = ConcreteDatabaseProvider(
            "sqlite:///test.db", connection_pool=mock_pool, query_logger=mock_logger,
        )
        await provider.connect()

        stats = await provider.get_stats()

        assert stats["connected"] is True
        assert stats["connection_pool"] is True
        assert stats["query_logger"] is True

    @pytest.mark.asyncio
    async def test_query_logging(self, mock_query_logger):
        """Test query logging functionality"""
        provider = ConcreteDatabaseProvider(
            "sqlite:///test.db", query_logger=mock_query_logger,
        )
        await provider.connect()

        await provider.execute_query("SELECT * FROM test_table", ["param"])

        # Verify logging was called
        mock_query_logger.log_query.assert_called_once()
        call_args = mock_query_logger.log_query.call_args[0][0]

        assert call_args.sql == "SELECT * FROM test_table"
        assert list(call_args.params) == ["param"]
        assert call_args.success is True
        assert call_args.execution_time >= 0

    @pytest.mark.asyncio
    async def test_query_logging_with_exception(self, mock_query_logger):
        """Test query logging when exception occurs"""
        provider = ConcreteDatabaseProvider(
            "sqlite:///test.db", query_logger=mock_query_logger,
        )
        await provider.connect()

        # Mock to raise exception
        original_method = provider._execute_query_raw

        async def failing_query(*args, **kwargs):
            raise RuntimeError("Query failed")

        provider._execute_query_raw = failing_query

        with pytest.raises(RuntimeError):
            await provider.execute_query("SELECT * FROM test_table")

        # Verify logging was called with failure
        mock_query_logger.log_query.assert_called_once()
        call_args = mock_query_logger.log_query.call_args[0][0]

        assert call_args.success is False
        assert "Query failed" in call_args.error_message

        # Restore original method
        provider._execute_query_raw = original_method

    @pytest.mark.asyncio
    async def test_connection_pool_context_manager(self, mock_connection_pool):
        """Test connection pool context manager usage"""
        provider = ConcreteDatabaseProvider(
            "sqlite:///test.db", connection_pool=mock_connection_pool,
        )
        await provider.connect()

        # Mock the connection from pool
        mock_conn = Mock()
        mock_connection_pool.get_connection.return_value.__aenter__.return_value = (
            mock_conn
        )

        # Execute a query (should use pool)
        # result = await provider.execute_query("SELECT 1")  # Not used in this test

        # Verify pool's context manager was used
        mock_connection_pool.get_connection.assert_called_once()
        mock_connection_pool.get_connection.return_value.__aenter__.assert_called_once()
        mock_connection_pool.get_connection.return_value.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_direct_connection_context_manager(self):
        """Test direct connection context manager usage"""
        provider = ConcreteDatabaseProvider("sqlite:///test.db")
        await provider.connect()

        # Execute a query (should use direct connection)
        # result = await provider.execute_query("SELECT 1")  # Not used in this test

        # Should not have created new connections since we already connected
        assert len(provider._connections_created) == 1
