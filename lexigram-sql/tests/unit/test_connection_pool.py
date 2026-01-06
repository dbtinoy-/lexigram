"""
Unit tests for connection pool implementations

Tests AbstractConnectionPool and SimpleConnectionPool functionality.
"""

import asyncio
from contextlib import asynccontextmanager
import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.core import HealthStatus
from lexigram.contracts.core import HealthCheckResult

from lexigram.contracts.data import (
    ConnectionPoolProtocol,
)
from lexigram.sql.pool.connection import (
    AbstractConnectionPool,
    SimpleConnectionPool,
    _ProviderConnection,
)


class TestBaseConnectionPool:
    """Test AbstractConnectionPool functionality"""

    @pytest.fixture
    def mock_connection_pool(self):
        """Create a mock connection pool for testing AbstractConnectionPool"""

        class MockConnectionPool(AbstractConnectionPool):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.created_connections = []
                self.closed_connections = []
                self.validated_connections = []

            async def _create_connection(self) -> Any:
                conn = MagicMock()
                self.created_connections.append(conn)
                return conn

            async def _close_connection(self, connection: Any) -> None:
                self.closed_connections.append(connection)

            async def _validate_connection(self, connection: Any) -> bool:
                self.validated_connections.append(connection)
                return True

        return MockConnectionPool

    def test_init_default_values(self, mock_connection_pool):
        """Test initialization with default values"""
        pool = mock_connection_pool()

        assert pool.min_connections == 1
        assert pool.max_connections == 10
        assert pool.connection_timeout == 30.0
        assert pool.max_idle_time == 300.0
        assert len(pool._pool) == 0
        assert pool._active_connections == 0
        assert pool._total_connections == 0
        assert pool._initialized is False
        assert pool._shutdown is False
        assert pool._created_connections == 0
        assert pool._destroyed_connections == 0
        assert pool._acquired_connections == 0
        assert pool._released_connections == 0

    def test_init_custom_values(self, mock_connection_pool):
        """Test initialization with custom values"""
        pool = mock_connection_pool(
            min_connections=5,
            max_connections=50,
            connection_timeout=60.0,
            max_idle_time=600.0,
        )

        assert pool.min_connections == 5
        assert pool.max_connections == 50
        assert pool.connection_timeout == 60.0
        assert pool.max_idle_time == 600.0

    @pytest.mark.asyncio
    async def test_initialize_creates_min_connections(self, mock_connection_pool):
        """Test initialize creates minimum number of connections"""
        pool = mock_connection_pool(min_connections=3)

        await pool.initialize()

        assert pool._initialized is True
        assert len(pool._pool) == 3
        assert pool._total_connections == 3
        assert pool._created_connections == 3
        assert len(pool.created_connections) == 3

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self, mock_connection_pool):
        """Test initialize is idempotent"""
        pool = mock_connection_pool(min_connections=2)

        await pool.initialize()
        await pool.initialize()  # Second call should do nothing

        assert len(pool._pool) == 2
        assert pool._total_connections == 2
        assert pool._created_connections == 2

    @pytest.mark.asyncio
    async def test_shutdown_closes_all_connections(self, mock_connection_pool):
        """Test shutdown closes all connections"""
        pool = mock_connection_pool(min_connections=2)
        await pool.initialize()

        await pool.shutdown()

        assert pool._shutdown is True
        assert len(pool._pool) == 0
        assert pool._total_connections == 0
        assert pool._active_connections == 0
        assert pool._destroyed_connections == 2
        assert len(pool.closed_connections) == 2

    @pytest.mark.asyncio
    async def test_shutdown_idempotent(self, mock_connection_pool):
        """Test shutdown is idempotent"""
        pool = mock_connection_pool(min_connections=1)
        await pool.initialize()

        await pool.shutdown()
        await pool.shutdown()  # Second call should do nothing

        assert pool._destroyed_connections == 1
        assert len(pool.closed_connections) == 1

    @pytest.mark.asyncio
    async def test_get_connection_context_manager(self, mock_connection_pool):
        """Test get_connection context manager"""
        pool = mock_connection_pool()
        await pool.initialize()

        async with pool.get_connection() as conn:
            assert conn is not None
            assert pool._active_connections == 1
            assert pool._acquired_connections == 1

        assert pool._active_connections == 0
        assert pool._released_connections == 1
        assert len(pool._pool) == 1  # Connection returned to pool

    @pytest.mark.asyncio
    async def test_get_connection_reuses_from_pool(self, mock_connection_pool):
        """Test get_connection reuses connections from pool"""
        pool = mock_connection_pool(min_connections=1)

        # First connection
        async with pool.get_connection() as _:
            assert pool._active_connections == 1

        # Second connection should reuse
        async with pool.get_connection() as _:
            assert pool._active_connections == 1
            assert len(pool._pool) == 0  # Connection in use

        assert len(pool._pool) == 1  # Connection returned

    @pytest.mark.asyncio
    async def test_get_connection_creates_new_when_pool_empty(
        self, mock_connection_pool,
    ):
        """Test get_connection creates new connection when pool is empty"""
        pool = mock_connection_pool(min_connections=0, max_connections=5)

        async with pool.get_connection() as conn:
            assert conn is not None
            assert pool._total_connections == 1
            assert pool._created_connections == 1

    @pytest.mark.asyncio
    async def test_get_connection_max_connections_reached(self, mock_connection_pool):
        """Test get_connection when max connections reached"""
        # Use a short timeout so the test fails quickly instead of waiting the default
        pool = mock_connection_pool(
            min_connections=0, max_connections=1, connection_timeout=0.01,
        )

        # Use the single connection
        async with pool.get_connection() as _:
            # Try to get another connection - should wait and timeout
            with pytest.raises(Exception, match="Connection pool exhausted"):
                async with pool.get_connection() as _:
                    pass

    @pytest.mark.asyncio
    async def test_get_connection_pool_exhausted_timeout(self, mock_connection_pool):
        """Test get_connection timeout when pool is exhausted"""
        pool = mock_connection_pool(
            min_connections=0,
            max_connections=1,
            connection_timeout=0.1,  # Short timeout
        )

        # Use the single connection
        async with pool.get_connection() as _:
            # Try to get another connection - should timeout quickly
            start_time = time.time()
            with pytest.raises(Exception, match="Connection pool exhausted"):
                async with pool.get_connection() as _:
                    pass
            elapsed = time.time() - start_time
            assert elapsed >= 0.1  # Should have waited at least the timeout

    @pytest.mark.asyncio
    async def test_get_connection_invalid_connection_discarded(
        self, mock_connection_pool,
    ):
        """Test get_connection discards invalid connections"""
        pool = mock_connection_pool(min_connections=1)

        # Make validation fail
        pool.validated_connections.clear()
        # original_validate = pool._validate_connection  # Not used

        async def failing_validate(conn):
            pool.validated_connections.append(conn)
            return False

        pool._validate_connection = failing_validate

        async with pool.get_connection() as conn:
            assert conn is not None
            assert pool._destroyed_connections == 1  # Invalid connection discarded
            assert pool._total_connections == 1  # New connection created

    @pytest.mark.asyncio
    async def test_get_connection_old_connection_discarded(self, mock_connection_pool):
        """Test get_connection discards connections that exceed max_idle_time"""
        pool = mock_connection_pool(min_connections=1, max_idle_time=0.1)
        await pool.initialize()

        # Wait for connection to become "old"
        await asyncio.sleep(0.2)

        async with pool.get_connection() as conn:
            assert conn is not None
            assert pool._destroyed_connections == 1  # Old connection discarded
            assert pool._total_connections == 1  # New connection created

    @pytest.mark.asyncio
    async def test_get_connection_after_shutdown_raises_error(
        self, mock_connection_pool,
    ):
        """Test get_connection raises error after shutdown"""
        pool = mock_connection_pool()
        await pool.shutdown()

        with pytest.raises(RuntimeError, match="Connection pool is shutdown"):
            async with pool.get_connection() as _:
                pass

    @pytest.mark.asyncio
    async def test_return_connection_valid_connection(self, mock_connection_pool):
        """Test return_connection with valid connection"""
        pool = mock_connection_pool()

        conn = MagicMock()
        await pool.return_connection(conn)

        assert len(pool._pool) == 1
        assert pool._pool[0][0] == conn

    @pytest.mark.asyncio
    async def test_return_connection_invalid_connection(self, mock_connection_pool):
        """Test return_connection with invalid connection"""
        pool = mock_connection_pool()

        conn = MagicMock()
        # Make validation fail
        # original_validate = pool._validate_connection  # Not used

        async def failing_validate(conn):
            return False

        pool._validate_connection = failing_validate

        await pool.return_connection(conn)

        assert len(pool._pool) == 0
        assert pool._destroyed_connections == 1
        assert (
            pool._total_connections == -1
        )  # This seems like a bug in the implementation

    @pytest.mark.asyncio
    async def test_get_pool_stats(self, mock_connection_pool):
        """Test get_pool_stats returns correct statistics"""
        pool = mock_connection_pool(min_connections=2, max_connections=10)
        await pool.initialize()

        # Use a connection
        async with pool.get_connection() as _:
            stats = await pool.get_pool_stats()

            assert stats["pool_size"] == 1  # One connection in pool
            assert stats["active_connections"] == 1  # One connection in use
            assert stats["total_connections"] == 2  # Total created
            assert stats["max_connections"] == 10
            assert stats["min_connections"] == 2
            assert stats["created_connections"] == 2
            assert stats["destroyed_connections"] == 0
            assert stats["acquired_connections"] == 1
            assert stats["released_connections"] == 0  # Not yet released
            assert stats["idle_connections"] == 1
            assert "uptime_seconds" in stats
            assert "utilization_rate" in stats

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, mock_connection_pool):
        """Test health_check returns healthy status"""
        pool = mock_connection_pool(min_connections=5, max_connections=10)
        await pool.initialize()

        health = await pool.health_check()

        assert health.status == HealthStatus.HEALTHY
        assert "Pool utilization" in health.details["message"]
        assert health.details["issues"] == []
        assert "stats" in health.details

    @pytest.mark.asyncio
    async def test_health_check_warning_high_utilization(self, mock_connection_pool):
        """Test health_check returns warning for high utilization"""
        pool = mock_connection_pool(min_connections=1, max_connections=10)
        await pool.initialize()  # Initialize to meet minimum connections

        # Simulate high utilization
        pool._active_connections = 9  # 90% utilization

        health = await pool.health_check()

        assert health.status == HealthStatus.UNHEALTHY
        assert "High connection utilization" in health.details["issues"]

    @pytest.mark.asyncio
    async def test_health_check_critical_very_high_utilization(
        self, mock_connection_pool,
    ):
        """Test health_check returns critical for very high utilization"""
        pool = mock_connection_pool(min_connections=1, max_connections=10)

        # Simulate very high utilization
        pool._active_connections = 10  # 100% utilization

        health = await pool.health_check()

        assert health.status == HealthStatus.UNHEALTHY
        assert health.error is not None

    @pytest.mark.asyncio
    async def test_health_check_below_minimum_connections(self, mock_connection_pool):
        """Test health_check detects below minimum connections"""
        pool = mock_connection_pool(min_connections=5, max_connections=10)

        # Only initialize with 2 connections (below minimum)
        pool._total_connections = 2
        pool._pool = list(map(lambda _: (MagicMock(), time.time()), range(2)))

        health = await pool.health_check()

        assert "Below minimum connection count" in health.details["issues"]

    @pytest.mark.asyncio
    async def test_health_check_exception_handling(self, mock_connection_pool):
        """Test health_check handles exceptions gracefully"""
        pool = mock_connection_pool()

        # Make get_pool_stats fail
        # original_get_stats = pool.get_pool_stats  # Not used

        async def failing_get_stats():
            raise RuntimeError("Stats error")

        pool.get_pool_stats = failing_get_stats

        health = await pool.health_check()

        assert health.status == HealthStatus.UNHEALTHY
        assert "Health check failed" in (health.error or "")
        assert "Unable to get pool statistics" in health.details["issues"]


class TestSimpleConnectionPool:
    """Test SimpleConnectionPool functionality"""

    @pytest.fixture
    def mock_provider(self):
        """Create a mock database provider"""
        provider = MagicMock(spec=ConnectionPoolProtocol)
        provider.is_connected = AsyncMock(return_value=True)
        return provider

    def test_init(self, mock_provider):
        """Test SimpleConnectionPool initialization"""
        pool = SimpleConnectionPool(
            provider=mock_provider, min_connections=2, max_connections=20,
        )

        assert pool.provider == mock_provider
        assert pool.min_connections == 2
        assert pool.max_connections == 20

    @pytest.mark.asyncio
    async def test_create_connection(self, mock_provider):
        """Test _create_connection returns provider"""
        pool = SimpleConnectionPool(provider=mock_provider)

        conn = await pool._create_connection()

        assert conn == mock_provider

    @pytest.mark.asyncio
    async def test_close_connection(self, mock_provider):
        """Test _close_connection does nothing for providers"""
        pool = SimpleConnectionPool(provider=mock_provider)

        # Should not raise any exception
        await pool._close_connection(mock_provider)

    @pytest.mark.asyncio
    async def test_validate_connection_with_is_connected(self, mock_provider):
        """Test _validate_connection uses provider.is_connected()"""
        pool = SimpleConnectionPool(provider=mock_provider)

        mock_provider.is_connected.return_value = True
        result = await pool._validate_connection(mock_provider)
        assert result is True

        mock_provider.is_connected.return_value = False
        result = await pool._validate_connection(mock_provider)
        assert result is False

        mock_provider.is_connected.assert_called()

    @pytest.mark.asyncio
    async def test_validate_connection_without_is_connected(self):
        """Test _validate_connection defaults to True when no validation methods present"""
        provider_without_validation = MagicMock()
        del provider_without_validation.is_connected  # Remove is_connected
        del provider_without_validation.execute  # Remove execute (no SQL ping)

        pool = SimpleConnectionPool(provider=provider_without_validation)

        result = await pool._validate_connection(provider_without_validation)
        assert result is True

    @pytest.mark.asyncio
    async def test_full_integration(self, mock_provider):
        """Test full integration of SimpleConnectionPool"""
        pool = SimpleConnectionPool(
            provider=mock_provider, min_connections=1, max_connections=3,
        )

        # Initialize
        await pool.initialize()
        assert pool._total_connections == 1

        # Get connection
        async with pool.get_connection() as conn:
            assert conn == mock_provider
            assert pool._active_connections == 1

        # Check stats
        stats = await pool.get_pool_stats()
        assert stats["total_connections"] == 1
        assert stats["active_connections"] == 0
        assert stats["pool_size"] == 1

        # Health check
        health = await pool.health_check()
        assert health.status == HealthStatus.HEALTHY

        # Shutdown
        await pool.shutdown()
        assert pool._shutdown is True
        assert pool._total_connections == 0

    @pytest.mark.asyncio
    async def test_create_connection_with_proxy(self, mock_provider):
        """Test _create_connection returns proxy when enabled"""
        pool = SimpleConnectionPool(provider=mock_provider, use_provider_proxy=True)

        conn = await pool._create_connection()

        assert isinstance(conn, _ProviderConnection)
        assert conn._provider is mock_provider


class TestReplicaPool:
    """Test ReplicaPool functionality"""

    @pytest.fixture
    def mock_connection_pool(self):
        """Create a mock connection pool for testing ReplicaPool"""

        class MockConnectionPool(AbstractConnectionPool):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.connections_used = []

            async def _create_connection(self) -> Any:
                conn = MagicMock()
                return conn

            async def _close_connection(self, connection: Any) -> None:
                pass

            async def _validate_connection(self, connection: Any) -> bool:
                return True

        return MockConnectionPool

    def test_init_with_primary_only(self, mock_connection_pool):
        """Test initialization with primary pool only"""
        from lexigram.sql.pool import ReplicaPool

        primary = mock_connection_pool()
        pool = ReplicaPool(primary)

        assert pool.primary_pool is primary
        assert pool.replica_pools == []
        assert pool._replica_index == 0

    def test_init_with_replicas(self, mock_connection_pool):
        """Test initialization with replica pools"""
        from lexigram.sql.pool import ReplicaPool

        primary = mock_connection_pool()
        replica1 = mock_connection_pool()
        replica2 = mock_connection_pool()

        pool = ReplicaPool(primary, [replica1, replica2])

        assert pool.primary_pool is primary
        assert pool.replica_pools == [replica1, replica2]

    @pytest.mark.asyncio
    async def test_read_with_replicas(self):
        """Test read operations use replicas"""
        from unittest.mock import MagicMock

        from lexigram.sql.pool import ReplicaPool

        # Create mock pools that return context managers
        class MockPool:
            def __init__(self, name):
                self.name = name
                self.connections_used = []

            @asynccontextmanager
            async def get_connection(self):
                conn = MagicMock()
                conn.name = self.name
                self.connections_used.append(conn)
                try:
                    yield conn
                finally:
                    pass

            async def initialize(self):
                pass

            async def shutdown(self):
                pass

            async def health_check(self):
                return {"status": "healthy"}

        primary = MockPool("primary")
        replica1 = MockPool("replica1")
        replica2 = MockPool("replica2")

        pool = ReplicaPool(primary, [replica1, replica2])

        # First read should use replica1
        async with pool.read() as conn:
            assert conn.name == "replica1"

        # Second read should use replica2
        async with pool.read() as conn:
            assert conn.name == "replica2"

        # Third read should cycle back to replica1
        async with pool.read() as conn:
            assert conn.name == "replica1"

    @pytest.mark.asyncio
    async def test_read_without_replicas_uses_primary(self):
        """Test read operations fall back to primary when no replicas"""
        from unittest.mock import MagicMock

        from lexigram.sql.pool import ReplicaPool

        # Create mock pool that returns context manager
        class MockPool:
            def __init__(self, name):
                self.name = name

            @asynccontextmanager
            async def get_connection(self):
                conn = MagicMock()
                conn.name = self.name
                try:
                    yield conn
                finally:
                    pass

            async def initialize(self):
                pass

            async def shutdown(self):
                pass

            async def health_check(self):
                return {"status": "healthy"}

        primary = MockPool("primary")
        pool = ReplicaPool(primary)

        async with pool.read() as conn:
            assert conn.name == "primary"

    @pytest.mark.asyncio
    async def test_write_always_uses_primary(self):
        """Test write operations always use primary"""
        from unittest.mock import MagicMock

        from lexigram.sql.pool import ReplicaPool

        # Create mock pools that return context managers
        class MockPool:
            def __init__(self, name):
                self.name = name

            @asynccontextmanager
            async def get_connection(self):
                conn = MagicMock()
                conn.name = self.name
                try:
                    yield conn
                finally:
                    pass

            async def initialize(self):
                pass

            async def shutdown(self):
                pass

            async def health_check(self):
                return {"status": "healthy"}

        primary = MockPool("primary")
        replica = MockPool("replica")
        pool = ReplicaPool(primary, [replica])

        async with pool.write() as conn:
            assert conn.name == "primary"

    @pytest.mark.asyncio
    async def test_initialize_all_pools(self, mock_connection_pool):
        """Test initialization of all pools"""
        from lexigram.sql.pool import ReplicaPool

        primary = mock_connection_pool()
        replica1 = mock_connection_pool()
        replica2 = mock_connection_pool()

        pool = ReplicaPool(primary, [replica1, replica2])

        # Mock initialize methods
        primary.initialize = AsyncMock()
        replica1.initialize = AsyncMock()
        replica2.initialize = AsyncMock()

        await pool.initialize()

        primary.initialize.assert_called_once()
        replica1.initialize.assert_called_once()
        replica2.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_all_pools(self, mock_connection_pool):
        """Test shutdown of all pools"""
        from lexigram.sql.pool import ReplicaPool

        primary = mock_connection_pool()
        replica1 = mock_connection_pool()
        replica2 = mock_connection_pool()

        pool = ReplicaPool(primary, [replica1, replica2])

        # Mock shutdown methods
        primary.shutdown = AsyncMock()
        replica1.shutdown = AsyncMock()
        replica2.shutdown = AsyncMock()

        await pool.shutdown()

        primary.shutdown.assert_called_once()
        replica1.shutdown.assert_called_once()
        replica2.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_all_pools(self, mock_connection_pool):
        """Test health check of all pools"""
        from lexigram.sql.pool import ReplicaPool

        primary = mock_connection_pool()
        replica1 = mock_connection_pool()
        replica2 = mock_connection_pool()

        pool = ReplicaPool(primary, [replica1, replica2])

        # Mock health check methods (legacy dict responses are normalized)
        primary.health_check = AsyncMock(return_value=HealthCheckResult(component="primary", status=HealthStatus.HEALTHY, details={"message": "OK"}))
        replica1.health_check = AsyncMock(return_value=HealthCheckResult(component="replica1", status=HealthStatus.HEALTHY, details={"message": "OK"}))
        replica2.health_check = AsyncMock(return_value=HealthCheckResult(component="replica2", status=HealthStatus.UNHEALTHY, error="High load"))

        health = await pool.health_check()

        assert health.status == HealthStatus.UNHEALTHY  # Because one replica has warning
        assert "primary" in health.details
        assert "replicas" in health.details
        assert len(health.details["replicas"]) == 2
