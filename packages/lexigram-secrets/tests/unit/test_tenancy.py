from __future__ import annotations

import pytest

from lexigram.secrets.tenancy import TenantScopedSecretStore
from lexigram.testing.fakes import FakeRotatableSecretStore


class TestTenantScopedSecretStore:
    @pytest.fixture
    def inner(self) -> FakeRotatableSecretStore:
        return FakeRotatableSecretStore()

    @pytest.fixture
    def tenant_a(self, inner: FakeRotatableSecretStore) -> TenantScopedSecretStore:
        return TenantScopedSecretStore(inner, "tenant_a")

    @pytest.fixture
    def tenant_b(self, inner: FakeRotatableSecretStore) -> TenantScopedSecretStore:
        return TenantScopedSecretStore(inner, "tenant_b")

    async def test_isolates_keys_between_tenants(
        self,
        tenant_a: TenantScopedSecretStore,
        tenant_b: TenantScopedSecretStore,
    ) -> None:
        await tenant_a.set("key", "a_value")
        await tenant_b.set("key", "b_value")
        assert await tenant_a.get("key") == "a_value"
        assert await tenant_b.get("key") == "b_value"

    async def test_get_missing_returns_none(
        self,
        tenant_a: TenantScopedSecretStore,
    ) -> None:
        result = await tenant_a.get("nonexistent")
        assert result is None

    async def test_delete_removes_tenant_key(
        self,
        tenant_a: TenantScopedSecretStore,
        inner: FakeRotatableSecretStore,
    ) -> None:
        await tenant_a.set("key", "val")
        await tenant_a.delete("key")
        assert await tenant_a.get("key") is None
        assert await inner.get("tenant_a/key") is None

    async def test_get_bulk_scoped(
        self,
        tenant_a: TenantScopedSecretStore,
        tenant_b: TenantScopedSecretStore,
    ) -> None:
        await tenant_a.set("a", "1")
        await tenant_b.set("b", "2")
        result = await tenant_a.get_bulk("a", "b")
        assert result == {"a": "1"}

    async def test_rotate_scoped(
        self,
        tenant_a: TenantScopedSecretStore,
        inner: FakeRotatableSecretStore,
    ) -> None:
        await tenant_a.set("key", "original")
        rotated = await tenant_a.rotate("key")
        assert rotated.key == "key"
        tenant_a_current = await tenant_a.get_current_version("key")
        assert str(tenant_a_current.value) != "original"

        inner_current = await inner.get_current_version("tenant_a/key")
        assert str(inner_current.value) == str(rotated.value)

    async def test_get_version_scoped(
        self,
        tenant_a: TenantScopedSecretStore,
    ) -> None:
        await tenant_a.set("key", "v1")
        result = await tenant_a.get_version("key", 1)
        assert result == "v1"

    async def test_list_versions_scoped(
        self,
        tenant_a: TenantScopedSecretStore,
    ) -> None:
        await tenant_a.set("key", "v1")
        await tenant_a.rotate("key")
        versions = await tenant_a.list_versions("key")
        assert len(versions) >= 2
