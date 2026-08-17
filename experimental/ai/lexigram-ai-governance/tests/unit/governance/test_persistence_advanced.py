"""Advanced unit tests for GovernancePersistence implementations — Redis and SQL."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.ai.governance.exceptions import GovernancePersistenceError
from lexigram.ai.governance.persistence.persistence import (
    DatabaseGovernancePersistence,
    RedisGovernancePersistence,
)
from lexigram.contracts.infra.cache.exceptions import CacheError
from lexigram.result import Err


@pytest.mark.asyncio
class TestRedisGovernancePersistence:
    @pytest.fixture
    def mock_cache(self) -> AsyncMock:
        cache = AsyncMock()
        cache.get.return_value = None
        return cache

    async def test_incr_requests_redis_native(self, mock_cache) -> None:
        # Mock native redis client inside cache
        mock_client = AsyncMock()
        mock_cache._client = mock_client
        mock_client.zcard.return_value = 5
        
        persistence = RedisGovernancePersistence(cache=mock_cache)
        count = await persistence.incr_requests("u1", window=60.0)
        
        assert count == 5
        mock_client.zremrangebyscore.assert_called_once()
        mock_client.zadd.assert_called_once()
        mock_client.expire.assert_called_once()

    async def test_incr_requests_fallback(self, mock_cache) -> None:
        # Ensure no native client is detected
        mock_cache._client = None
        mock_cache.client = None
        # No native client, use get/set fallback
        mock_cache.get.return_value = "10"
        
        persistence = RedisGovernancePersistence(cache=mock_cache)
        count = await persistence.incr_requests("u1", window=60.0)
        
        assert count == 11
        mock_cache.get.assert_called_once()
        mock_cache.set.assert_called_once()

    async def test_add_spend_success(self, mock_cache) -> None:
        mock_cache.get.return_value = "1.5"
        
        persistence = RedisGovernancePersistence(cache=mock_cache)
        total = await persistence.add_spend("k1", 0.5, ttl=3600)
        
        assert total == 2.0
        mock_cache.set.assert_called_with("ai:gov:spend:k1", "2.0", ttl=3600)

    async def test_add_spend_propagates_backend_failure(self, mock_cache) -> None:
        """Infrastructure failures propagate instead of returning the amount."""
        mock_cache.get.side_effect = RuntimeError("redis down")

        persistence = RedisGovernancePersistence(cache=mock_cache)
        with pytest.raises(RuntimeError, match="redis down"):
            await persistence.add_spend("k1", 0.5, ttl=3600)


@pytest.mark.asyncio
class TestRedisPersistenceFailClosed:
    """All five enforcement methods propagate failures (fail-closed, §50)."""

    @pytest.fixture
    def err_cache(self) -> AsyncMock:
        cache = AsyncMock()
        cache._client = None
        cache.client = None
        cache.get.return_value = Err(CacheError("redis down"))
        cache.set.return_value = Err(CacheError("redis down"))
        return cache

    @pytest.fixture
    def raising_cache(self) -> AsyncMock:
        cache = AsyncMock()
        cache._client = None
        cache.client = None
        cache.get.side_effect = RuntimeError("redis down")
        return cache

    @pytest.mark.parametrize(
        ("method", "args"),
        [
            ("incr_requests", ("u1", 60.0)),
            ("add_spend", ("k1", 0.5, 3600)),
            ("get_spend", ("k1",)),
            ("read_gauge", ("k1",)),
            ("incr_gauge", ("k1", 5.0, 3600)),
        ],
    )
    async def test_err_result_raises_governance_persistence_error(
        self, err_cache: AsyncMock, method: str, args: tuple
    ) -> None:
        """An Err result from a protocol-compliant backend raises, not 0/1/amount."""
        persistence = RedisGovernancePersistence(cache=err_cache)
        with pytest.raises(GovernancePersistenceError, match="redis down"):
            await getattr(persistence, method)(*args)

    @pytest.mark.parametrize(
        ("method", "args"),
        [
            ("incr_requests", ("u1", 60.0)),
            ("add_spend", ("k1", 0.5, 3600)),
            ("get_spend", ("k1",)),
            ("read_gauge", ("k1",)),
            ("incr_gauge", ("k1", 5.0, 3600)),
        ],
    )
    async def test_raised_backend_error_propagates(
        self, raising_cache: AsyncMock, method: str, args: tuple
    ) -> None:
        """A raised backend error propagates unmodified (matches DatabaseGovernancePersistence)."""
        persistence = RedisGovernancePersistence(cache=raising_cache)
        with pytest.raises(RuntimeError, match="redis down"):
            await getattr(persistence, method)(*args)


@pytest.mark.asyncio
class TestDatabaseGovernancePersistence:
    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        return AsyncMock()

    async def test_ensure_tables_on_first_call(self, mock_db) -> None:
        persistence = DatabaseGovernancePersistence(db=mock_db)
        await persistence.get_spend("k1")
        
        # Verify DDL was executed
        assert mock_db.execute.call_count >= 2
        assert "CREATE TABLE" in mock_db.execute.call_args_list[0][0][0]
        
        # Call again, should not execute DDL
        await persistence.get_spend("k1")
        assert mock_db.execute.call_count == 4

    async def test_incr_requests_sql(self, mock_db) -> None:
        mock_result = MagicMock()
        mock_result.rows = [{"cnt": 3}]
        mock_db.execute_query.return_value = mock_result
        
        persistence = DatabaseGovernancePersistence(db=mock_db)
        count = await persistence.incr_requests("u1", window=60.0)
        
        assert count == 3
        assert mock_db.execute.call_count >= 3 # 2 for tables + 1 for insert + 1 for prune
        
    async def test_add_spend_sql(self, mock_db) -> None:
        from unittest.mock import ANY
        mock_result = MagicMock()
        mock_result.rows = [{"amount": 5.5}]
        mock_db.execute_query.return_value = mock_result
        
        persistence = DatabaseGovernancePersistence(db=mock_db)
        total = await persistence.add_spend("k1", 1.0, ttl=3600)
        
        assert total == 5.5
        mock_db.execute.assert_any_call(
            "INSERT INTO ai_governance_spend (key, amount, expires_at) VALUES (?, ?, ?) "
            "ON CONFLICT (key) DO UPDATE SET "
            "amount = amount + excluded.amount, "
            "expires_at = excluded.expires_at",
            ANY
        )
