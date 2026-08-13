"""Tests for gauge/calendar methods on GovernancePersistence (LXF-001).

RED phase — these tests fail because the gauge/calendar methods don't exist yet.
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock

import pytest
from lexigram.ai.governance.persistence import (
    DatabaseGovernancePersistence,
    GovernancePersistence,
    InMemoryGovernancePersistence,
    RedisGovernancePersistence,
)


@pytest.fixture
def in_memory() -> InMemoryGovernancePersistence:
    return InMemoryGovernancePersistence()


@pytest.fixture
def redis_persistence() -> RedisGovernancePersistence:
    return RedisGovernancePersistence(cache=AsyncMock())


@pytest.fixture
def db_persistence() -> DatabaseGovernancePersistence:
    db = AsyncMock()
    db.execute = AsyncMock()
    db.execute_query = AsyncMock()
    db.execute_query.return_value = MagicMock(rows=[])
    return DatabaseGovernancePersistence(db=db)


class TestProtocolConformance:
    def test_read_gauge_in_protocol(self):
        """read_gauge should be part of the GovernancePersistence protocol."""
        assert hasattr(GovernancePersistence, "read_gauge")

    def test_write_gauge_in_protocol(self):
        """write_gauge should be part of the GovernancePersistence protocol."""
        assert hasattr(GovernancePersistence, "write_gauge")

    def test_add_calendar_entry_in_protocol(self):
        """add_calendar_entry should be part of the GovernancePersistence protocol."""
        assert hasattr(
            GovernancePersistence, "add_calendar_entry"
        )

    def test_query_calendar_in_protocol(self):
        """query_calendar should be part of the GovernancePersistence protocol."""
        assert hasattr(GovernancePersistence, "query_calendar")

    def test_incr_gauge_in_protocol(self):
        """incr_gauge should be part of the GovernancePersistence protocol."""
        assert hasattr(GovernancePersistence, "incr_gauge")


class TestInMemoryGauge:
    @pytest.mark.asyncio
    async def test_write_then_read(self, in_memory):
        await in_memory.write_gauge("tenant:gpt4:remaining", 50000, ttl=3600)
        val = await in_memory.read_gauge("tenant:gpt4:remaining")
        assert val == 50000

    @pytest.mark.asyncio
    async def test_read_missing_returns_zero(self, in_memory):
        val = await in_memory.read_gauge("nonexistent")
        assert val == 0

    @pytest.mark.asyncio
    async def test_read_missing_model_returns_zero(self, in_memory):
        val = await in_memory.read_gauge("tenant:other_model")
        assert val == 0

    @pytest.mark.asyncio
    async def test_incr_gauge(self, in_memory):
        await in_memory.write_gauge("key1", 100, ttl=3600)
        new_val = await in_memory.incr_gauge("key1", -10, ttl=3600)
        assert new_val == 90

    @pytest.mark.asyncio
    async def test_incr_gauge_missing(self, in_memory):
        new_val = await in_memory.incr_gauge("new_key", 50, ttl=3600)
        assert new_val == 50

    @pytest.mark.asyncio
    async def test_incr_gauge_negative_result(self, in_memory):
        new_val = await in_memory.incr_gauge("neg_key", -100, ttl=3600)
        assert new_val == 0

    @pytest.mark.asyncio
    async def test_overwrite_gauge_value(self, in_memory):
        await in_memory.write_gauge("key", 100, ttl=3600)
        await in_memory.write_gauge("key", 200, ttl=3600)
        val = await in_memory.read_gauge("key")
        assert val == 200


class TestInMemoryCalendar:
    @pytest.mark.asyncio
    async def test_add_and_query_entry(self, in_memory):
        now = time.time()
        await in_memory.add_calendar_entry("tenant:gpt4:daily", now, ttl=86400)
        results = await in_memory.query_calendar(
            "tenant:gpt4:daily", start=now - 1, end=now + 1
        )
        assert len(results) == 1
        assert abs(results[0] - now) < 0.001

    @pytest.mark.asyncio
    async def test_query_empty_calendar(self, in_memory):
        results = await in_memory.query_calendar("unknown", start=0, end=1e12)
        assert results == []

    @pytest.mark.asyncio
    async def test_query_outside_range(self, in_memory):
        now = time.time()
        await in_memory.add_calendar_entry("key", now, ttl=86400)
        results = await in_memory.query_calendar("key", start=now + 10, end=now + 20)
        assert results == []

    @pytest.mark.asyncio
    async def test_multiple_entries(self, in_memory):
        now = time.time()
        for i in range(5):
            await in_memory.add_calendar_entry("multi", now + i, ttl=86400)
        results = await in_memory.query_calendar("multi", start=now, end=now + 10)
        assert len(results) == 5


class TestRedisGauge:
    @pytest.mark.asyncio
    async def test_read_gauge_triggers_cache_get(self, redis_persistence):
        redis_persistence._cache.get = AsyncMock(return_value="42")
        val = await redis_persistence.read_gauge("test_key")
        assert val == 42

    @pytest.mark.asyncio
    async def test_read_gauge_missing(self, redis_persistence):
        redis_persistence._cache.get = AsyncMock(return_value=None)
        val = await redis_persistence.read_gauge("missing")
        assert val == 0

    @pytest.mark.asyncio
    async def test_write_gauge_triggers_cache_set(self, redis_persistence):
        redis_persistence._cache.set = AsyncMock()
        await redis_persistence.write_gauge("k", 999, ttl=3600)
        redis_persistence._cache.set.assert_awaited_once_with(
            "ai:gov:gauge:k", "999", ttl=3600
        )

    @pytest.mark.asyncio
    async def test_incr_gauge(self, redis_persistence):
        redis_persistence._cache.get = AsyncMock(return_value="100")
        redis_persistence._cache.set = AsyncMock()
        val = await redis_persistence.incr_gauge("counter", 5, ttl=3600)
        assert val == 105

    @pytest.mark.asyncio
    async def test_incr_gauge_missing(self, redis_persistence):
        redis_persistence._cache.get = AsyncMock(return_value=None)
        redis_persistence._cache.set = AsyncMock()
        val = await redis_persistence.incr_gauge("new", 10, ttl=3600)
        assert val == 10


class TestRedisCalendar:
    @pytest.mark.asyncio
    async def test_add_and_query(self, redis_persistence):
        redis_persistence._cache.get = AsyncMock(return_value=None)
        redis_persistence._cache.set = AsyncMock()
        now = time.time()
        await redis_persistence.add_calendar_entry("cal:key", now, ttl=86400)
        # After adding, the cached value should contain the entry
        redis_persistence._cache.get = AsyncMock(return_value=str(now))
        results = await redis_persistence.query_calendar(
            "cal:key", start=now - 1, end=now + 1
        )
        assert len(results) >= 1


class TestDatabaseGauge:
    @pytest.mark.asyncio
    async def test_write_gauge_creates_row(self, db_persistence):
        db_persistence._db.execute_query.return_value = MagicMock(rows=[])
        await db_persistence.write_gauge("test", 42, ttl=3600)
        assert db_persistence._db.execute.call_count >= 1

    @pytest.mark.asyncio
    async def test_read_gauge_returns_value(self, db_persistence):
        db_persistence._db.execute_query.return_value = MagicMock(
            rows=[{"value": 42}]
        )
        val = await db_persistence.read_gauge("test")
        assert val == 42

    @pytest.mark.asyncio
    async def test_read_gauge_missing(self, db_persistence):
        db_persistence._db.execute_query.return_value = MagicMock(rows=[])
        val = await db_persistence.read_gauge("nonexistent")
        assert val == 0

    @pytest.mark.asyncio
    async def test_incr_gauge(self, db_persistence):
        db_persistence._db.execute_query.return_value = MagicMock(
            rows=[{"value": 100}]
        )
        val = await db_persistence.incr_gauge("counter", 50, ttl=3600)
        assert val == 150


class TestDatabaseCalendar:
    @pytest.mark.asyncio
    async def test_add_and_query(self, db_persistence):
        db_persistence._db.execute_query.return_value = MagicMock(
            rows=[{"ts": 1000.0}, {"ts": 1001.0}]
        )
        results = await db_persistence.query_calendar(
            "cal", start=900.0, end=1100.0
        )
        assert len(results) == 2
        assert results[0] == 1000.0

    @pytest.mark.asyncio
    async def test_query_empty(self, db_persistence):
        db_persistence._db.execute_query.return_value = MagicMock(rows=[])
        results = await db_persistence.query_calendar(
            "empty", start=0, end=1e12
        )
        assert results == []
