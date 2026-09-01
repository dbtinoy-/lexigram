"""Settings writes must detect conflicts at write time, not only before.

Comparing a revision token in the controller and then writing
unconditionally leaves a time-of-check/time-of-use window: two sessions can
read the same revision, both pass the comparison, and both write, so the
later write silently discards the earlier one. These tests pin the
conditional-write path that re-checks inside the write itself.
"""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.admin.services.settings_service import (
    KEY_PREFIX,
    AdminSettingsDbProvider,
    AdminSettingsService,
)
from lexigram.admin.settings.conflict import SettingsConflictError
from lexigram.admin.settings.panel import CacheSpec
from lexigram.admin.settings.panel.registry import (
    ConfigRegistry,
    MemoryStore,
    StoreBase,
)
from lexigram.admin.settings.store import TenantConfigStore


class _Txn:
    """Minimal async transaction context recording commit/rollback."""

    def __init__(self, db: _Db) -> None:
        self._db = db

    async def __aenter__(self) -> Any:
        self._db.depth += 1
        return self

    async def __aexit__(self, exc_type: Any, *_: Any) -> bool:
        self._db.depth -= 1
        if exc_type is not None:
            self._db.rolled_back = True
        return False


class _Db:
    """In-memory stand-in for a transactional database provider."""

    def __init__(self, rows: dict[str, Any] | None = None) -> None:
        self.rows: dict[str, Any] = dict(rows or {})
        self.statements: list[Any] = []
        self.depth = 0
        self.rolled_back = False

    def transaction(self, isolation_level: Any = None) -> Any:
        return _Txn(self)

    async def execute(self, sql: str, params: Any = None) -> Any:
        if sql.strip().upper().startswith("SELECT KEY"):
            return type(
                "R",
                (),
                {"rows": [{"key": k, "value": v} for k, v in self.rows.items()]},
            )()
        self.statements.append((sql, params))
        return None


def _provider(rows: dict[str, Any] | None = None) -> tuple[AdminSettingsDbProvider, _Db]:
    db = _Db(rows)
    provider = AdminSettingsDbProvider(db)  # type: ignore[arg-type]
    provider._initialized = True
    return provider, db


class TestProviderConditionalWrite:
    """The DB provider re-checks stored values inside the transaction."""

    @pytest.mark.asyncio
    async def test_write_applies_when_nothing_changed(self) -> None:
        provider, db = _provider({"a": '"old"'})

        await provider.set_config_many_if_unchanged(
            "t1", {"a": "new"}, {"a": "old"}
        )

        assert len(db.statements) == 1
        assert not db.rolled_back

    @pytest.mark.asyncio
    async def test_conflict_raises_and_writes_nothing(self) -> None:
        provider, db = _provider({"a": '"changed-by-someone-else"'})

        with pytest.raises(SettingsConflictError):
            await provider.set_config_many_if_unchanged(
                "t1", {"a": "new"}, {"a": "old"}
            )

        assert db.statements == []

    @pytest.mark.asyncio
    async def test_conflict_rolls_the_transaction_back(self) -> None:
        provider, db = _provider({"a": '"changed"'})

        with pytest.raises(SettingsConflictError):
            await provider.set_config_many_if_unchanged(
                "t1", {"a": "new"}, {"a": "old"}
            )

        assert db.rolled_back

    @pytest.mark.asyncio
    async def test_check_happens_inside_the_transaction(self) -> None:
        """A check outside the transaction would not close the race."""
        provider, db = _provider({"a": '"old"'})
        depths: list[int] = []

        original = provider.get_all_config

        async def _spy(tenant_id: str) -> dict[str, Any]:
            depths.append(db.depth)
            return await original(tenant_id)

        provider.get_all_config = _spy  # type: ignore[method-assign]

        await provider.set_config_many_if_unchanged("t1", {"a": "new"}, {"a": "old"})

        assert depths == [1]

    @pytest.mark.asyncio
    async def test_conflict_names_the_changed_keys(self) -> None:
        provider, _ = _provider({"a": '"x"', "b": '"y"'})

        with pytest.raises(SettingsConflictError, match="a, b"):
            await provider.set_config_many_if_unchanged(
                "t1", {"a": "1", "b": "2"}, {"a": "old", "b": "old"}
            )

    @pytest.mark.asyncio
    async def test_absent_row_is_not_a_conflict(self) -> None:
        """An unwritten key rendered as its default; nobody raced us."""
        provider, db = _provider({})

        await provider.set_config_many_if_unchanged(
            "t1", {"a": "new"}, {"a": "default"}
        )

        assert len(db.statements) == 1

    @pytest.mark.asyncio
    async def test_empty_items_is_a_no_op(self) -> None:
        provider, db = _provider({"a": '"changed"'})

        await provider.set_config_many_if_unchanged("t1", {}, {"a": "old"})

        assert db.statements == []

    @pytest.mark.asyncio
    async def test_boolean_round_trip_is_not_a_false_conflict(self) -> None:
        """Forms submit "true"/"false" strings; storage returns booleans."""
        provider, db = _provider({"flag": "true"})

        await provider.set_config_many_if_unchanged(
            "t1", {"flag": "false"}, {"flag": True}
        )

        assert len(db.statements) == 1

    @pytest.mark.asyncio
    async def test_numeric_round_trip_is_not_a_false_conflict(self) -> None:
        provider, db = _provider({"ttl": "300"})

        await provider.set_config_many_if_unchanged(
            "t1", {"ttl": "600"}, {"ttl": 300}
        )

        assert len(db.statements) == 1


class TestServiceConditionalWrite:
    """The service layer maps names to keys and honours conflicts."""

    @pytest.mark.asyncio
    async def test_memory_backend_detects_conflict(self) -> None:
        service = AdminSettingsService()
        await service.set("t1", "site_name", "Live Value")

        with pytest.raises(SettingsConflictError):
            await service.set_many_if_unchanged(
                "t1", {"site_name": "Mine"}, {"site_name": "Stale Value"}
            )

        assert await service.get("t1", "site_name") == "Live Value"

    @pytest.mark.asyncio
    async def test_memory_backend_writes_when_unchanged(self) -> None:
        service = AdminSettingsService()
        await service.set("t1", "site_name", "Current")

        await service.set_many_if_unchanged(
            "t1", {"site_name": "Next"}, {"site_name": "Current"}
        )

        assert await service.get("t1", "site_name") == "Next"

    @pytest.mark.asyncio
    async def test_expected_keys_are_prefixed_for_the_provider(self) -> None:
        provider, _ = _provider({f"{KEY_PREFIX}site_name": '"Current"'})
        service = AdminSettingsService(provider)  # type: ignore[arg-type]

        await service.set_many_if_unchanged(
            "t1", {"site_name": "Next"}, {"site_name": "Current"}
        )

    @pytest.mark.asyncio
    async def test_provider_conflict_propagates(self) -> None:
        provider, _ = _provider({f"{KEY_PREFIX}site_name": '"Someone Else"'})
        service = AdminSettingsService(provider)  # type: ignore[arg-type]

        with pytest.raises(SettingsConflictError):
            await service.set_many_if_unchanged(
                "t1", {"site_name": "Mine"}, {"site_name": "Stale"}
            )

    @pytest.mark.asyncio
    async def test_legacy_provider_falls_back_without_failing(self) -> None:
        """An older provider must not break saves, only lose the guarantee."""

        class _LegacyProvider:
            def __init__(self) -> None:
                self.written: dict[str, Any] = {}

            async def set_config(self, tenant_id: str, key: str, value: Any) -> None:
                self.written[key] = value

            async def get_config(self, tenant_id: str, key: str) -> Any:
                return self.written.get(key)

            async def get_all_config(self, tenant_id: str) -> dict[str, Any]:
                return dict(self.written)

        legacy = _LegacyProvider()
        service = AdminSettingsService(legacy)  # type: ignore[arg-type]

        await service.set_many_if_unchanged(
            "t1", {"site_name": "Next"}, {"site_name": "Whatever"}
        )

        assert legacy.written[f"{KEY_PREFIX}site_name"] == "Next"
        assert service.supports_conditional_write() is False

    @pytest.mark.asyncio
    async def test_capability_is_reported_for_modern_provider(self) -> None:
        provider, _ = _provider({})
        service = AdminSettingsService(provider)  # type: ignore[arg-type]

        assert service.supports_conditional_write() is True


class TestStoreAdapter:
    """TenantConfigStore forwards conditional writes to the service."""

    @pytest.mark.asyncio
    async def test_conditional_write_reaches_the_service(self) -> None:
        service = AdminSettingsService()
        await service.set("default", "admin.cache.enabled", "true")
        store = TenantConfigStore(service)

        with pytest.raises(SettingsConflictError):
            await store.set_many_if_unchanged(
                {"admin.cache.enabled": "false"},
                {"admin.cache.enabled": "stale"},
            )

    @pytest.mark.asyncio
    async def test_capability_probe_is_forwarded(self) -> None:
        store = TenantConfigStore(AdminSettingsService())

        assert await store.supports_conditional_write() is True


class TestStoreBaseDefaults:
    """The base class degrades safely rather than pretending to be atomic."""

    @pytest.mark.asyncio
    async def test_default_conditional_write_delegates(self) -> None:
        store = MemoryStore()

        await store.set_many_if_unchanged({"a": "1"}, {"a": "anything"})

        assert await store.get("a") == "1"

    @pytest.mark.asyncio
    async def test_default_does_not_claim_support(self) -> None:
        assert await StoreBase().supports_conditional_write() is False


class TestRegistryConditionalWrite:
    """save_values routes to the conditional path only when asked."""

    @pytest.mark.asyncio
    async def test_expected_values_are_namespaced(self) -> None:
        registry = ConfigRegistry()
        registry.register_spec(CacheSpec)
        seen: dict[str, Any] = {}

        class _Recording(MemoryStore):
            async def set_many_if_unchanged(
                self,
                items: dict[str, Any],
                expected: dict[str, Any],
                tenant_id: str | None = None,
            ) -> None:
                seen["items"] = dict(items)
                seen["expected"] = dict(expected)

        registry.register_store("test", _Recording())

        await registry.save_values(
            "admin.cache",
            {"enabled": "true"},
            store_name="test",
            expected={"enabled": False},
        )

        assert seen["items"] == {"admin.cache.enabled": True}
        assert seen["expected"] == {"admin.cache.enabled": False}

    @pytest.mark.asyncio
    async def test_omitting_expected_uses_unconditional_write(self) -> None:
        registry = ConfigRegistry()
        registry.register_spec(CacheSpec)
        calls: list[str] = []

        class _Recording(MemoryStore):
            async def set_many(
                self, items: dict[str, Any], tenant_id: str | None = None
            ) -> None:
                calls.append("set_many")

            async def set_many_if_unchanged(
                self,
                items: dict[str, Any],
                expected: dict[str, Any],
                tenant_id: str | None = None,
            ) -> None:
                calls.append("conditional")

        registry.register_store("test", _Recording())

        await registry.save_values(
            "admin.cache", {"enabled": "true"}, store_name="test"
        )

        assert calls == ["set_many"]

    @pytest.mark.asyncio
    async def test_unknown_expected_keys_are_dropped(self) -> None:
        """Only spec-declared nodes may take part in the comparison."""
        registry = ConfigRegistry()
        registry.register_spec(CacheSpec)
        seen: dict[str, Any] = {}

        class _Recording(MemoryStore):
            async def set_many_if_unchanged(
                self,
                items: dict[str, Any],
                expected: dict[str, Any],
                tenant_id: str | None = None,
            ) -> None:
                seen["expected"] = dict(expected)

        registry.register_store("test", _Recording())

        await registry.save_values(
            "admin.cache",
            {"enabled": "true"},
            store_name="test",
            expected={"enabled": False, "bogus": "x"},
        )

        assert seen["expected"] == {"admin.cache.enabled": False}

    @pytest.mark.asyncio
    async def test_capability_probe_tolerates_a_broken_store(self) -> None:
        registry = ConfigRegistry()

        class _Broken(MemoryStore):
            async def supports_conditional_write(self) -> bool:
                raise RuntimeError("store is down")

        registry.register_store("test", _Broken())

        assert await registry.supports_conditional_write("test") is False
