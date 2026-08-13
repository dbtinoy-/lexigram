"""Tests for the idempotency module including store and decorator."""

from __future__ import annotations

import asyncio

import pytest

from lexigram.resilience.decorators import idempotent
from lexigram.resilience.idempotency.store import InMemoryIdempotencyStore


class TestInMemoryIdempotencyStore:
    """Tests for InMemoryIdempotencyStore."""

    @pytest.fixture
    def store(self) -> InMemoryIdempotencyStore:
        return InMemoryIdempotencyStore()

    @pytest.mark.asyncio
    async def test_set_and_get(self, store: InMemoryIdempotencyStore) -> None:
        """Store and retrieve a value by key."""
        await store.set("key1", {"result": True})
        assert await store.get("key1") == {"result": True}

    @pytest.mark.asyncio
    async def test_get_missing_returns_none(
        self, store: InMemoryIdempotencyStore
    ) -> None:
        """Getting a non-existent key returns None."""
        assert await store.get("nonexistent") is None

    @pytest.mark.asyncio
    async def test_delete_removes_entry(self, store: InMemoryIdempotencyStore) -> None:
        """Delete removes a stored entry."""
        await store.set("key1", "value")
        await store.delete("key1")
        assert await store.get("key1") is None

    @pytest.mark.asyncio
    async def test_ttl_expiry(self, store: InMemoryIdempotencyStore) -> None:
        """Entries with exceeded TTL return None."""
        await store.set("key1", "value", ttl=0.01)
        await asyncio.sleep(0.05)
        assert await store.get("key1") is None

    @pytest.mark.asyncio
    async def test_no_ttl_persists(self, store: InMemoryIdempotencyStore) -> None:
        """Entries without TTL never expire."""
        await store.set("key1", "value", ttl=None)
        assert await store.get("key1") == "value"

    def test_clear(self, store: InMemoryIdempotencyStore) -> None:
        """clear() removes all entries."""
        store._store["a"] = ("val", None)
        store.clear()
        assert len(store._store) == 0


class TestIdempotentDecorator:
    """Tests for the @idempotent decorator."""

    @pytest.mark.asyncio
    async def test_first_call_executes(self) -> None:
        """First call to decorated function executes and caches result."""
        store = InMemoryIdempotencyStore()
        call_count = 0

        @idempotent(store, ttl=60.0)
        async def do_work(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        result = await do_work(5)
        assert result == 10
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_second_call_returns_cached(self) -> None:
        """Second call with same args returns cached result without re-executing."""
        store = InMemoryIdempotencyStore()
        call_count = 0

        @idempotent(store, ttl=60.0)
        async def do_work(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        await do_work(5)
        result = await do_work(5)
        assert result == 10
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_different_args_execute_separately(self) -> None:
        """Different arguments produce different cache keys and both execute."""
        store = InMemoryIdempotencyStore()
        call_count = 0

        @idempotent(store, ttl=60.0)
        async def do_work(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        await do_work(5)
        await do_work(10)
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_custom_key_func(self) -> None:
        """Custom key function determines cache key instead of default."""
        store = InMemoryIdempotencyStore()
        call_count = 0

        @idempotent(store, key_func=lambda x: f"fixed-{x}", ttl=60.0)
        async def do_work(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x

        await do_work(1)
        await do_work(1)
        assert call_count == 1


class TestMaxEntries:
    """Tests for InMemoryIdempotencyStore max_entries cap."""

    @pytest.mark.asyncio
    async def test_within_limit_stores_all(self) -> None:
        """Entries within the cap are all stored."""
        store = InMemoryIdempotencyStore(max_entries=3)
        await store.set("a", 1)
        await store.set("b", 2)
        await store.set("c", 3)
        assert store.size == 3

    @pytest.mark.asyncio
    async def test_exceeding_limit_evicts_oldest(self) -> None:
        """Adding a fourth entry when max_entries=3 evicts the first inserted."""
        store = InMemoryIdempotencyStore(max_entries=3)
        await store.set("a", 1)
        await store.set("b", 2)
        await store.set("c", 3)
        await store.set("d", 4)  # should evict "a"
        assert store.size == 3
        assert await store.get("a") is None
        assert await store.get("d") == 4

    @pytest.mark.asyncio
    async def test_update_existing_key_does_not_evict(self) -> None:
        """Updating an existing key does not count as a new entry."""
        store = InMemoryIdempotencyStore(max_entries=2)
        await store.set("a", 1)
        await store.set("b", 2)
        await store.set("a", 99)  # update, not insert
        assert store.size == 2
        assert await store.get("a") == 99
        assert await store.get("b") == 2

    @pytest.mark.asyncio
    async def test_no_max_entries_unbounded(self) -> None:
        """Without max_entries the store grows without eviction."""
        store = InMemoryIdempotencyStore()
        for i in range(10):
            await store.set(str(i), i)
        assert store.size == 10


class TestIdempotentDecoratorConcurrency:
    """Tests verifying the TOCTOU race fix in the idempotent decorator."""

    @pytest.mark.asyncio
    async def test_concurrent_calls_with_same_key_execute_once(self) -> None:
        """Two concurrent coroutines with the same key execute the function exactly once."""
        store = InMemoryIdempotencyStore()
        execution_count = 0

        @idempotent(store, ttl=60.0)
        async def expensive_operation(value: int) -> int:
            nonlocal execution_count
            # Yield to event loop to allow the TOCTOU race to manifest if unfixed.
            await asyncio.sleep(0)
            execution_count += 1
            return value * 2

        results = await asyncio.gather(
            expensive_operation(5),
            expensive_operation(5),
        )

        # Both must return the same value.
        assert results[0] == results[1] == 10
        # With the per-key lock, the function body must execute exactly once.
        assert execution_count == 1

    @pytest.mark.asyncio
    async def test_concurrent_calls_with_different_keys_both_execute(self) -> None:
        """Concurrent calls with different keys each execute independently."""
        store = InMemoryIdempotencyStore()
        execution_count = 0

        @idempotent(store, ttl=60.0)
        async def my_op(value: int) -> int:
            nonlocal execution_count
            await asyncio.sleep(0)
            execution_count += 1
            return value

        results = await asyncio.gather(
            my_op(1),
            my_op(2),
        )

        assert sorted(results) == [1, 2]
        assert execution_count == 2

    @pytest.mark.asyncio
    async def test_second_call_returns_cached_result_without_executing(self) -> None:
        """Sequential calls with the same key only execute the function the first time."""
        store = InMemoryIdempotencyStore()
        execution_count = 0

        @idempotent(store, ttl=60.0)
        async def my_op() -> str:
            nonlocal execution_count
            execution_count += 1
            return "result"

        first = await my_op()
        second = await my_op()

        assert first == second == "result"
        assert execution_count == 1
