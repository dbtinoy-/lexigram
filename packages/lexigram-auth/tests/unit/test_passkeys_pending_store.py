import pytest

from lexigram.auth.authn.passkeys import _PendingStore


class DummyCache:
    def __init__(self):
        self._store = {}

    async def set(self, key, value, ex=None):
        self._store[key] = value

    async def get(self, key):
        return self._store.get(key)

    async def delete(self, key):
        self._store.pop(key, None)


@pytest.mark.asyncio
async def test_pending_store_inmemory():
    s = _PendingStore()
    await s.set("k1", {"x": 1}, ttl=1)
    v = await s.get("k1")
    assert v == {"x": 1}
    await s.delete("k1")
    assert await s.get("k1") is None


@pytest.mark.asyncio
async def test_pending_store_cache_backend():
    cache = DummyCache()
    s = _PendingStore(cache)

    await s.set("k2", {"y": 2}, ttl=10)
    v = await s.get("k2")
    assert v == {"y": 2}
    await s.delete("k2")
    assert await s.get("k2") is None
