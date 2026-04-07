# packages/lexigram/tests/unit/components/test_distributed_lock.py

import asyncio
from unittest.mock import AsyncMock

import pytest

from lexigram.cache.locks import DistributedLockProtocol


@pytest.fixture
def redis_client():
    """In-memory mock Redis client."""
    store: dict = {}
    client = AsyncMock()

    async def mock_set(key, value, *, nx=False, ex=None):
        if nx and key in store:
            return None
        store[key] = value
        return True

    async def mock_get(key):
        return store.get(key)

    async def mock_delete(*keys):
        for key in keys:
            store.pop(key, None)
        return len(keys)

    client.set = AsyncMock(side_effect=mock_set)
    client.get = AsyncMock(side_effect=mock_get)
    client.delete = AsyncMock(side_effect=mock_delete)
    client.expire.return_value = 1
    return client


class TestDistributedLock:
    """Test distributed lock with auto-renewal."""

    @pytest.mark.asyncio
    async def test_acquire_and_release(self, redis_client):
        """Test basic acquire and release."""
        lock = DistributedLockProtocol(redis_client, key="test-lock", ttl=10)

        # Acquire
        acquired = await lock.acquire()
        assert acquired
        assert lock.is_locked

        # Release
        released = await lock.release()
        assert released
        assert not lock.is_locked

    @pytest.mark.asyncio
    async def test_auto_renewal(self, redis_client):
        """Test lock TTL is automatically renewed every renewal_interval seconds."""
        lock = DistributedLockProtocol(
            redis_client,
            key="test-lock",
            ttl=10,
            renewal_interval=1,
        )

        await lock.acquire()

        # Wait for at least one renewal cycle
        await asyncio.sleep(2)

        # redis.expire should have been called at least once
        assert redis_client.expire.call_count >= 1

        await lock.release()

    @pytest.mark.asyncio
    async def test_context_manager(self, redis_client):
        """Test async context manager via lock.lock()."""
        lock = DistributedLockProtocol(redis_client, key="test-lock", ttl=30)

        async with lock.lock():
            assert lock.is_locked

        assert not lock.is_locked

    @pytest.mark.asyncio
    async def test_acquire_fails_when_already_held(self):
        """Test acquire returns False when the Redis SET NX fails."""
        busy_redis = AsyncMock()
        busy_redis.set = AsyncMock(return_value=None)  # NX fails — lock busy

        lock = DistributedLockProtocol(busy_redis, key="test-lock", ttl=30)

        acquired = await lock.acquire()
        assert not acquired
        assert not lock.is_locked

    @pytest.mark.asyncio
    async def test_renewal_stops_on_release(self, redis_client):
        """Test renewal task is cancelled when lock is released."""
        lock = DistributedLockProtocol(redis_client, key="test-lock", ttl=10, renewal_interval=1)

        await lock.acquire()
        renewal_task = lock._lock_info.renewal_task  # type: ignore[union-attr]

        await lock.release()

        # Renewal task should be done (either cancelled or finished)
        assert renewal_task.done()
