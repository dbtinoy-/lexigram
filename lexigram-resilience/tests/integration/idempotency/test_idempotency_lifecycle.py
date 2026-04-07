"""Integration tests for the lexigram-idempotency provider lifecycle.

Tests the complete DI lifecycle for the idempotency subsystem using the
real Container and in-memory store — no external services required.

Flow under test:
  IdempotencyProvider.register() → IdempotencyProvider.boot()
  → resolve IdempotencyStoreProtocol → key acquire / get / set / delete
  → IdempotencyProvider.shutdown()
"""

from __future__ import annotations

import pytest

from lexigram.contracts.core.idempotency import IdempotencyStoreProtocol
from lexigram.di.container import Container
from lexigram.resilience.config import IdempotencyConfig
from lexigram.resilience.idempotency.store import InMemoryIdempotencyStore
from lexigram.resilience.idempotency.provider import IdempotencyProvider

pytestmark = [pytest.mark.integration]


class TestIdempotencyProviderLifecycle:
    """Full provider lifecycle for the in-memory idempotency store.

    Exercises the register → boot → resolve → key operations → shutdown
    sequence using the real DI Container and InMemoryIdempotencyStore.
    """

    @pytest.fixture
    async def booted_container(self):
        """Container with IdempotencyProvider fully registered and booted."""
        provider = IdempotencyProvider(config=IdempotencyConfig(auto_cleanup=False))
        container = Container()
        await provider.register(container)
        await provider.boot(container)
        yield container
        await provider.shutdown()

    # ------------------------------------------------------------------
    # register phase
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_register_binds_store_protocol(self) -> None:
        """IdempotencyStoreProtocol singleton is bound after register()."""
        provider = IdempotencyProvider(config=IdempotencyConfig(auto_cleanup=False))
        container = Container()

        await provider.register(container)

        store = await container.resolve(IdempotencyStoreProtocol)

        assert store is not None
        await provider.shutdown()

    @pytest.mark.asyncio
    async def test_register_binds_in_memory_implementation(self) -> None:
        """The bound implementation is an InMemoryIdempotencyStore."""
        provider = IdempotencyProvider(config=IdempotencyConfig(auto_cleanup=False))
        container = Container()

        await provider.register(container)

        store = await container.resolve(IdempotencyStoreProtocol)

        assert isinstance(store, InMemoryIdempotencyStore)
        await provider.shutdown()

    # ------------------------------------------------------------------
    # boot phase
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_boot_completes_without_error(
        self, booted_container: Container
    ) -> None:
        """boot() completes successfully — no boot-time work is expected."""
        store = await booted_container.resolve(IdempotencyStoreProtocol)

        assert store is not None

    @pytest.mark.asyncio
    async def test_singleton_returns_same_instance_on_repeated_resolution(
        self, booted_container: Container
    ) -> None:
        """Resolving IdempotencyStoreProtocol twice returns the same singleton."""
        store_a = await booted_container.resolve(IdempotencyStoreProtocol)
        store_b = await booted_container.resolve(IdempotencyStoreProtocol)

        assert store_a is store_b

    # ------------------------------------------------------------------
    # idempotency key operations — end-to-end
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_acquire_returns_true_for_new_key(
        self, booted_container: Container
    ) -> None:
        """acquire() returns True when claiming a key for the first time."""
        store = await booted_container.resolve(IdempotencyStoreProtocol)

        acquired = await store.acquire("key-new-001", ttl=60)

        assert acquired is True

    @pytest.mark.asyncio
    async def test_acquire_returns_false_for_already_held_key(
        self, booted_container: Container
    ) -> None:
        """acquire() returns False when the key is already claimed."""
        store = await booted_container.resolve(IdempotencyStoreProtocol)
        key = "key-double-002"

        first = await store.acquire(key, ttl=60)
        second = await store.acquire(key, ttl=60)

        assert first is True
        assert second is False

    @pytest.mark.asyncio
    async def test_set_and_get_round_trip(self, booted_container: Container) -> None:
        """set() stores a result that get() retrieves successfully."""
        store = await booted_container.resolve(IdempotencyStoreProtocol)
        key = "key-roundtrip-003"
        payload = {"order_id": "ord-123", "status": "created"}

        await store.set(key, payload)
        retrieved = await store.get(key)

        assert retrieved == payload

    @pytest.mark.asyncio
    async def test_has_returns_true_after_set(
        self, booted_container: Container
    ) -> None:
        """has() returns True for a key that was stored via set()."""
        store = await booted_container.resolve(IdempotencyStoreProtocol)
        key = "key-has-004"

        await store.set(key, "result-value")
        exists = await store.has(key)

        assert exists is True

    @pytest.mark.asyncio
    async def test_has_returns_false_for_missing_key(
        self, booted_container: Container
    ) -> None:
        """has() returns False for a key that was never stored."""
        store = await booted_container.resolve(IdempotencyStoreProtocol)

        exists = await store.has("key-missing-005")

        assert exists is False

    @pytest.mark.asyncio
    async def test_delete_removes_stored_key(self, booted_container: Container) -> None:
        """delete() removes a stored key so subsequent get() returns None."""
        store = await booted_container.resolve(IdempotencyStoreProtocol)
        key = "key-delete-006"

        await store.set(key, "to-be-deleted")
        await store.delete(key)
        retrieved = await store.get(key)

        assert retrieved is None

    @pytest.mark.asyncio
    async def test_full_idempotency_workflow(self, booted_container: Container) -> None:
        """Complete acquire → process → store → retrieve idempotency flow."""
        store = await booted_container.resolve(IdempotencyStoreProtocol)
        key = "key-workflow-007"

        # Step 1 — first caller acquires the key
        acquired = await store.acquire(key, ttl=60)
        assert acquired is True

        # Step 2 — a concurrent caller cannot acquire the same key
        duplicate = await store.acquire(key, ttl=60)
        assert duplicate is False

        # Step 3 — after processing, store the result
        operation_result = {"invoice_id": "inv-789", "total": 99.95}
        await store.set(key, operation_result)

        # Step 4 — downstream consumers retrieve the cached result
        cached = await store.get(key)
        assert cached == operation_result

    # ------------------------------------------------------------------
    # max_entries eviction
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_max_entries_evicts_oldest_on_overflow(self) -> None:
        """When max_entries is exceeded the oldest entry is evicted (FIFO)."""
        provider = IdempotencyProvider(
            config=IdempotencyConfig(max_entries=2, auto_cleanup=False)
        )
        container = Container()
        await provider.register(container)
        await provider.boot(container)

        store = await container.resolve(IdempotencyStoreProtocol)

        await store.set("first", "v1")
        await store.set("second", "v2")
        # Inserting "third" must evict "first" (the oldest entry)
        await store.set("third", "v3")

        assert await store.get("first") is None
        assert await store.get("second") == "v2"
        assert await store.get("third") == "v3"

        await provider.shutdown()

    # ------------------------------------------------------------------
    # shutdown
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_shutdown_is_idempotent(self) -> None:
        """Calling shutdown() twice must not raise."""
        provider = IdempotencyProvider(config=IdempotencyConfig(auto_cleanup=False))
        container = Container()
        await provider.register(container)
        await provider.boot(container)

        await provider.shutdown()
        await provider.shutdown()
