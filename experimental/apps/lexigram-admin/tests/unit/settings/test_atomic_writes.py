"""Multi-key settings writes must not half-apply.

``save_values`` previously wrote one key at a time, so a failure part-way
through a batch left earlier keys committed. These tests pin the
validate-then-write-as-a-batch behaviour.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from lexigram.admin.services.settings_service import AdminSettingsService
from lexigram.admin.settings.panel import CacheSpec
from lexigram.admin.settings.panel.registry import (
    ConfigRegistry,
    MemoryStore,
    StoreBase,
)
from lexigram.admin.settings.store import TenantConfigStore


class _FailOnNthSet(StoreBase):
    """Store whose per-key ``set`` explodes on the nth call."""

    def __init__(self, fail_on: int) -> None:
        self.data: dict[str, Any] = {}
        self._fail_on = fail_on
        self._calls = 0

    async def get(
        self, key: str, default: Any = None, tenant_id: str | None = None
    ) -> Any:
        return self.data.get(key, default)

    async def set(self, key: str, value: Any, tenant_id: str | None = None) -> None:
        self._calls += 1
        if self._calls == self._fail_on:
            raise RuntimeError("store write failed")
        self.data[key] = value


class TestStoreBaseSetMany:
    @pytest.mark.asyncio
    async def test_default_set_many_writes_every_key(self) -> None:
        store = MemoryStore()
        await store.set_many({"a": 1, "b": 2})
        assert await store.get("a") == 1
        assert await store.get("b") == 2

    @pytest.mark.asyncio
    async def test_memory_store_set_many_applies_all_at_once(self) -> None:
        store = MemoryStore()
        await store.set_many({"x": "1", "y": "2", "z": "3"})
        assert store._data == {"x": "1", "y": "2", "z": "3"}


class TestRegistryBatching:
    @pytest.mark.asyncio
    async def test_save_values_writes_one_batch(self) -> None:
        registry = ConfigRegistry()
        registry.register_spec(CacheSpec)
        store = AsyncMock()
        registry.register_store("test", store)

        await registry.save_values(
            "admin.cache",
            {"enabled": "true", "default_ttl": "120"},
            store_name="test",
        )

        store.set_many.assert_awaited_once()
        written = store.set_many.await_args.args[0]
        assert written == {
            "admin.cache.enabled": True,
            "admin.cache.default_ttl": 120,
        }

    @pytest.mark.asyncio
    async def test_validation_runs_before_any_key_is_written(self) -> None:
        """Every value is coerced up front, then written as one batch.

        ``validate`` intentionally falls back to defaults rather than raising
        (it also loads legacy config), so the guarantee here is ordering:
        nothing reaches the store until the whole batch has been resolved.
        """
        registry = ConfigRegistry()
        registry.register_spec(CacheSpec)

        observed: list[dict[str, Any]] = []

        class _RecordingStore(MemoryStore):
            async def set_many(
                self, items: dict[str, Any], tenant_id: str | None = None
            ) -> None:
                observed.append(dict(items))
                await super().set_many(items, tenant_id=tenant_id)

        registry.register_store("test", _RecordingStore())

        await registry.save_values(
            "admin.cache",
            {"enabled": "true", "default_ttl": "not-a-number"},
            store_name="test",
        )

        # One batch containing every coerced key — never a key at a time.
        assert len(observed) == 1
        assert set(observed[0]) == {
            "admin.cache.enabled",
            "admin.cache.default_ttl",
        }

    @pytest.mark.asyncio
    async def test_no_editable_values_skips_the_store(self) -> None:
        registry = ConfigRegistry()
        registry.register_spec(CacheSpec)
        store = AsyncMock()
        registry.register_store("test", store)

        await registry.save_values("admin.cache", {"unknown": "x"}, store_name="test")

        store.set_many.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_partial_failure_is_visible_to_the_caller(self) -> None:
        """The default sequential fallback still surfaces the error."""
        registry = ConfigRegistry()
        registry.register_spec(CacheSpec)
        store = _FailOnNthSet(fail_on=2)
        registry.register_store("test", store)

        with pytest.raises(RuntimeError):
            await registry.save_values(
                "admin.cache",
                {"enabled": "true", "default_ttl": "120"},
                store_name="test",
            )


class TestSettingsServiceBatch:
    @pytest.mark.asyncio
    async def test_set_many_without_provider_uses_memory(self) -> None:
        service = AdminSettingsService()
        await service.set_many("t1", {"a": 1, "b": 2})
        assert await service.get("t1", "a") == 1
        assert await service.get("t1", "b") == 2

    @pytest.mark.asyncio
    async def test_set_many_prefers_provider_batch_api(self) -> None:
        provider = AsyncMock()
        service = AdminSettingsService(config_provider=provider)

        await service.set_many("t1", {"a": 1, "b": 2})

        provider.set_config_many.assert_awaited_once()
        tenant, items = provider.set_config_many.await_args.args
        assert tenant == "t1"
        assert set(items.values()) == {1, 2}

    @pytest.mark.asyncio
    async def test_set_many_falls_back_to_per_key_writes(self) -> None:
        class _NoBatch:
            def __init__(self) -> None:
                self.calls: list[tuple[str, str, Any]] = []

            async def get_config(self, tenant_id: str, key: str) -> Any:
                return None

            async def get_all_config(self, tenant_id: str) -> dict[str, Any]:
                return {}

            async def set_config(self, tenant_id: str, key: str, value: Any) -> None:
                self.calls.append((tenant_id, key, value))

        provider = _NoBatch()
        service = AdminSettingsService(config_provider=provider)

        await service.set_many("t1", {"a": 1, "b": 2})

        assert len(provider.calls) == 2

    @pytest.mark.asyncio
    async def test_empty_batch_is_a_noop(self) -> None:
        provider = AsyncMock()
        service = AdminSettingsService(config_provider=provider)
        await service.set_many("t1", {})
        provider.set_config_many.assert_not_awaited()


class TestTenantConfigStoreBatch:
    @pytest.mark.asyncio
    async def test_set_many_delegates_to_service_batch(self) -> None:
        service = AsyncMock()
        store = TenantConfigStore(service=service, tenant_id="tenant-a")

        await store.set_many({"admin.cache.enabled": True})

        service.set_many.assert_awaited_once()
        tenant, items = service.set_many.await_args.args
        assert tenant == "tenant-a"
        assert items == {"admin.cache.enabled": True}

    @pytest.mark.asyncio
    async def test_explicit_tenant_overrides_default(self) -> None:
        service = AsyncMock()
        store = TenantConfigStore(service=service, tenant_id="tenant-a")

        await store.set_many({"k": "v"}, tenant_id="tenant-b")

        assert service.set_many.await_args.args[0] == "tenant-b"

    @pytest.mark.asyncio
    async def test_service_without_batch_api_falls_back(self) -> None:
        """Services predating set_many must keep working (non-atomically)."""

        class _LegacyService:
            def __init__(self) -> None:
                self.writes: list[tuple[str, str, Any]] = []

            async def get(self, tenant: str, name: str) -> Any:
                return None

            async def set(self, tenant: str, name: str, value: Any) -> None:
                self.writes.append((tenant, name, value))

        service = _LegacyService()
        store = TenantConfigStore(service=service, tenant_id="t1")  # type: ignore[arg-type]

        await store.set_many({"a": 1, "b": 2})

        assert service.writes == [("t1", "a", 1), ("t1", "b", 2)]


class TestDbProviderTransaction:
    @pytest.mark.asyncio
    async def test_batch_upsert_runs_inside_a_transaction(self) -> None:
        from lexigram.admin.services.settings_service import AdminSettingsDbProvider

        entered = False
        exited = False

        class _Txn:
            async def __aenter__(self) -> Any:
                nonlocal entered
                entered = True
                return self

            async def __aexit__(self, *exc: Any) -> bool:
                nonlocal exited
                exited = True
                return False

        class _Db:
            def __init__(self) -> None:
                self.statements: list[Any] = []

            def transaction(self, isolation_level: Any = None) -> Any:
                return _Txn()

            async def execute(self, sql: str, params: Any = None) -> Any:
                self.statements.append(params)
                return None

        db = _Db()
        provider = AdminSettingsDbProvider(db)  # type: ignore[arg-type]
        provider._initialized = True

        await provider.set_config_many("t1", {"a": 1, "b": 2})

        assert entered and exited
        assert len(db.statements) == 2
