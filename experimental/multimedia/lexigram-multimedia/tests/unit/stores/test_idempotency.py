import pytest

from lexigram.multimedia.stores import InMemoryIdempotencyStoreFallback


@pytest.mark.asyncio
async def test_set_then_get_round_trips() -> None:
    store = InMemoryIdempotencyStoreFallback()

    await store.set("key-1", {"status": "submitted"})

    assert await store.get("key-1") == {"status": "submitted"}


@pytest.mark.asyncio
async def test_get_missing_key_returns_none() -> None:
    store = InMemoryIdempotencyStoreFallback()

    assert await store.get("missing") is None


@pytest.mark.asyncio
async def test_get_record_aliases_get() -> None:
    store = InMemoryIdempotencyStoreFallback()
    await store.set("key-1", {"status": "submitted"})

    assert await store.get_record("key-1") == {"status": "submitted"}


@pytest.mark.asyncio
async def test_delete_removes_key() -> None:
    store = InMemoryIdempotencyStoreFallback()
    await store.set("key-1", {"status": "submitted"})

    await store.delete("key-1")

    assert await store.get("key-1") is None


@pytest.mark.asyncio
async def test_acquire_is_exclusive() -> None:
    store = InMemoryIdempotencyStoreFallback()

    assert await store.acquire("lock-1") is True
    assert await store.acquire("lock-1") is False

    await store.delete("lock-1")

    assert await store.acquire("lock-1") is True
