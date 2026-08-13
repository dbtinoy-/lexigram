"""Focused tests for the Redis lock store."""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.cache.stores.redis_lock import RedisLockStore
from lexigram.contracts.exceptions.components import (
    LockAcquisitionError,
    LockNotHeldError,
)
from lexigram.contracts.core.health import HealthStatus


class _FakeClient:
    def __init__(self) -> None:
        self.set_result: Any = True
        self.eval_result: Any = 1
        self.exists_result: Any = 0
        self.ping_result: Any | Exception = True
        self.set_calls: list[tuple] = []
        self.eval_calls: list[tuple] = []
        self.pinged = 0

    async def set(self, key: str, value: str, px: int, nx: bool) -> Any:
        self.set_calls.append((key, value, px, nx))
        return self.set_result

    async def eval(self, script: str, numkeys: int, *args: Any) -> Any:
        self.eval_calls.append((script, numkeys, args))
        return self.eval_result

    async def exists(self, key: str) -> Any:
        return self.exists_result

    async def ping(self) -> Any:
        self.pinged += 1
        if isinstance(self.ping_result, Exception):
            raise self.ping_result
        return self.ping_result


@pytest.mark.asyncio
async def test_acquire_requires_owner() -> None:
    store = RedisLockStore(client=_FakeClient())
    with pytest.raises(ValueError, match="owner parameter is required"):
        await store.acquire("res")


@pytest.mark.asyncio
async def test_acquire_success_with_prefix() -> None:
    client = _FakeClient()
    store = RedisLockStore(prefix="tenant1:", client=client)
    lock_id = await store.acquire("res", ttl=30, owner="svc")
    assert lock_id is not None
    assert lock_id.startswith("svc:")
    assert client.set_calls[0][0] == "tenant1:lock:res"
    assert client.set_calls[0][2] == 30000
    assert client.set_calls[0][3] is True


@pytest.mark.asyncio
async def test_acquire_failure_returns_none() -> None:
    client = _FakeClient()
    client.set_result = None
    store = RedisLockStore(client=client)
    assert await store.acquire("res", owner="svc") is None


@pytest.mark.asyncio
async def test_release_success() -> None:
    client = _FakeClient()
    client.eval_result = 1
    store = RedisLockStore(client=client)
    assert await store.release("res", "svc:abc") is None
    assert client.eval_calls[0][2][0] == "lock:res"


@pytest.mark.asyncio
async def test_release_not_held_raises() -> None:
    client = _FakeClient()
    client.eval_result = -1
    store = RedisLockStore(client=client)
    with pytest.raises(LockNotHeldError):
        await store.release("res", "svc:abc")


@pytest.mark.asyncio
async def test_release_ownership_mismatch_raises() -> None:
    client = _FakeClient()
    client.eval_result = 0
    store = RedisLockStore(client=client)
    with pytest.raises(LockNotHeldError):
        await store.release("res", "other:abc")


@pytest.mark.asyncio
async def test_extend_success() -> None:
    client = _FakeClient()
    client.eval_result = 1
    store = RedisLockStore(client=client)
    assert await store.extend("res", "svc:abc", ttl=60) is None
    script, numkeys, args = client.eval_calls[0]
    assert numkeys == 1
    assert args[1] == "svc:abc"
    assert args[2] == 60000


@pytest.mark.asyncio
async def test_extend_not_held_raises() -> None:
    client = _FakeClient()
    client.eval_result = -1
    store = RedisLockStore(client=client)
    with pytest.raises(LockNotHeldError):
        await store.extend("res", "svc:abc", ttl=60)


@pytest.mark.asyncio
async def test_extend_ownership_mismatch_raises() -> None:
    client = _FakeClient()
    client.eval_result = 0
    store = RedisLockStore(client=client)
    with pytest.raises(LockNotHeldError):
        await store.extend("res", "other:abc", ttl=60)


@pytest.mark.asyncio
async def test_is_locked_true() -> None:
    client = _FakeClient()
    client.exists_result = 1
    store = RedisLockStore(prefix="p:", client=client)
    assert await store.is_locked("res") is True


@pytest.mark.asyncio
async def test_is_locked_false() -> None:
    client = _FakeClient()
    client.exists_result = 0
    store = RedisLockStore(client=client)
    assert await store.is_locked("res") is False


@pytest.mark.asyncio
async def test_locked_context_manager_success() -> None:
    client = _FakeClient()
    client.eval_result = 1
    store = RedisLockStore(client=client)
    async with store.locked("res", owner="svc") as lock_id:
        assert lock_id is not None


@pytest.mark.asyncio
async def test_locked_context_manager_acquire_failure_raises() -> None:
    client = _FakeClient()
    client.set_result = None
    store = RedisLockStore(client=client)
    with pytest.raises(LockAcquisitionError):
        async with store.locked("res", owner="svc"):
            pytest.fail("should not enter")


@pytest.mark.asyncio
async def test_locked_context_manager_release_failure_propagates() -> None:
    client = _FakeClient()
    client.eval_result = -1
    store = RedisLockStore(client=client)
    with pytest.raises(LockNotHeldError):
        async with store.locked("res", owner="svc"):
            pass


@pytest.mark.asyncio
async def test_health_check_healthy() -> None:
    store = RedisLockStore(url="redis://x", client=_FakeClient())
    result = await store.health_check()
    assert result.status is HealthStatus.HEALTHY
    assert result.component == "lock_store"


@pytest.mark.asyncio
async def test_health_check_unhealthy() -> None:
    client = _FakeClient()
    client.ping_result = ConnectionError("down")
    store = RedisLockStore(url="redis://x", client=client)
    result = await store.health_check()
    assert result.status is HealthStatus.UNHEALTHY
    assert "down" in result.error


@pytest.mark.asyncio
async def test_lazy_client_requires_redis_driver(monkeypatch: pytest.MonkeyPatch) -> None:
    import lexigram.cache.stores.redis_lock as module

    monkeypatch.setattr(module, "HAS_REDIS", False)
    store = RedisLockStore()
    with pytest.raises(ImportError, match="Redis driver is required"):
        await store._get_client()