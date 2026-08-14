"""Tests for the multi-tenancy support layer."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.admin.multitenancy import (
    TenantConfig,
    TenantNotFoundError,
    TenantScopedDataSource,
)


# ---------------------------------------------------------------------------
# TenantConfig
# ---------------------------------------------------------------------------

class TestTenantConfig:
    def test_valid_config(self) -> None:
        config = TenantConfig(tenant_id="acme", name="Acme Corp")
        assert config.tenant_id == "acme"
        assert config.active is True

    def test_raises_on_empty_id(self) -> None:
        with pytest.raises(ValueError, match="tenant_id"):
            TenantConfig(tenant_id="", name="Acme")

    def test_raises_on_empty_name(self) -> None:
        with pytest.raises(ValueError, match="name"):
            TenantConfig(tenant_id="acme", name="")

    def test_optional_fields_default(self) -> None:
        config = TenantConfig(tenant_id="x", name="X")
        assert config.domain == ""
        assert config.metadata == {}


# ---------------------------------------------------------------------------
# TenantScopedDataSource


# ---------------------------------------------------------------------------
# TenantScopedDataSource
# ---------------------------------------------------------------------------

class TestTenantScopedDataSource:
    def _mock_ds(self) -> MagicMock:
        ds = MagicMock()
        ds.list = AsyncMock(return_value=[])
        ds.find_one = AsyncMock(return_value={"id": "1", "tenant_id": "acme"})
        ds.create = AsyncMock(return_value={"id": "1", "tenant_id": "acme"})
        ds.update = AsyncMock(return_value={"id": "1"})
        ds.delete = AsyncMock(return_value=True)
        return ds

    @pytest.mark.asyncio
    async def test_list_calls_underlying(self) -> None:
        ds = self._mock_ds()
        scoped = TenantScopedDataSource(ds, tenant_id="acme")
        query = MagicMock()
        query.add_filter = MagicMock()
        await scoped.list(query)
        query.add_filter.assert_called_once_with("tenant_id", "eq", "acme")
        ds.list.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_injects_tenant(self) -> None:
        ds = self._mock_ds()
        scoped = TenantScopedDataSource(ds, tenant_id="acme")
        await scoped.create({"name": "Test"})
        ds.create.assert_awaited_once_with({"name": "Test", "tenant_id": "acme"})

    @pytest.mark.asyncio
    async def test_find_one_returns_record_for_matching_tenant(self) -> None:
        ds = self._mock_ds()
        scoped = TenantScopedDataSource(ds, tenant_id="acme")
        record = await scoped.find_one("1")
        assert record is not None

    @pytest.mark.asyncio
    async def test_find_one_returns_none_for_wrong_tenant(self) -> None:
        ds = self._mock_ds()
        ds.find_one = AsyncMock(return_value={"id": "1", "tenant_id": "other"})
        scoped = TenantScopedDataSource(ds, tenant_id="acme")
        record = await scoped.find_one("1")
        assert record is None

    @pytest.mark.asyncio
    async def test_delete_delegates(self) -> None:
        ds = self._mock_ds()
        scoped = TenantScopedDataSource(ds, tenant_id="acme")
        result = await scoped.delete("1")
        assert result is True
        ds.delete.assert_awaited_once_with("1")

    def test_tenant_id_property(self) -> None:
        ds = MagicMock()
        scoped = TenantScopedDataSource(ds, tenant_id="acme")
        assert scoped.tenant_id == "acme"
