import pytest

from lexigram.multimedia.idempotency_store import InMemoryIdempotencyStoreFallback


@pytest.mark.asyncio
async def test_set_then_get_round_trips() -> None:
    store = InMemoryIdempotencyStoreFallback()

    await store.set("key-1", {"status": "submitted"})

    assert await store.get("key-1") == {"status": "submitted"}


@pytest.mark.asyncio
async def test_get_missing_key_returns_none() -> None:
    store = InMemoryIdempotencyStoreFallback()

    assert await store.get("missing") is None
