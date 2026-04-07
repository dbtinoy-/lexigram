"""Advanced unit tests for GovernancePersistence implementations — Redis and SQL."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
import pytest
import time

from lexigram.ai.governance.persistence.persistence import (
    RedisGovernancePersistence,
    DatabaseGovernancePersistence,
)


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

    async def test_add_spend_fail_open(self, mock_cache) -> None:
        mock_cache.get.side_effect = RuntimeError("redis down")
        
        persistence = RedisGovernancePersistence(cache=mock_cache)
        total = await persistence.add_spend("k1", 0.5, ttl=3600)
        
        assert total == 0.5 # returns the increment amount on failure


@pytest.mark.asyncio
class TestDatabaseGovernancePersistence:
    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        db = AsyncMock()
        return db

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
