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


@pytest.mark.asyncio
async def test_set_with_ttl_expires(monkeypatch) -> None:
    """Entries written with a TTL must be treated as absent after expiry."""
    import lexigram.multimedia.stores.idempotency as idem_mod

    current = 1000.0

    def fake_monotonic() -> float:
        return current

    monkeypatch.setattr(idem_mod.ambient_clock, "monotonic", fake_monotonic)

    store = InMemoryIdempotencyStoreFallback()
    await store.set("key-1", {"status": "submitted"}, ttl=60)

    current = 1059.0
    assert await store.get("key-1") == {"status": "submitted"}

    current = 1061.0  # past the 60s window
    assert await store.get("key-1") is None


@pytest.mark.asyncio
async def test_acquire_with_ttl_releases_after_expiry(monkeypatch) -> None:
    import lexigram.multimedia.stores.idempotency as idem_mod

    current = 0.0

    def fake_monotonic() -> float:
        return current

    monkeypatch.setattr(idem_mod.ambient_clock, "monotonic", fake_monotonic)

    store = InMemoryIdempotencyStoreFallback()
    assert await store.acquire("lock-1", ttl=10) is True
    assert await store.acquire("lock-1", ttl=10) is False

    current = 11.0
    assert await store.acquire("lock-1", ttl=10) is True


@pytest.mark.asyncio
async def test_without_ttl_never_expires() -> None:
    store = InMemoryIdempotencyStoreFallback()
    await store.set("key-1", "value")

    assert await store.get("key-1") == "value"
