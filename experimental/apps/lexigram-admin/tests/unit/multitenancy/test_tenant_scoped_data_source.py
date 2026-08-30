"""Tests for TenantScopedDataSource."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.admin.multitenancy.data_source import TenantScopedDataSource


class _QueryWithAddFilter:
    """A query-like object that supports add_filter()."""

    def __init__(self) -> None:
        self.filters: list[tuple[str, str, str]] = []

    def add_filter(self, field: str, op: str, value: str) -> None:
        self.filters.append((field, op, value))


class _QueryWithoutAddFilter:
    """A query-like object that does NOT support add_filter()."""


class TestTenantScopedDataSource:
    @pytest.fixture
    def mock_ds(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def scoped(self, mock_ds: AsyncMock) -> TenantScopedDataSource:
        return TenantScopedDataSource(mock_ds, tenant_id="tenant-acme")

    # -- list() --

    @pytest.mark.asyncio
    async def test_query_spec_is_scoped_without_mutating_original(
        self, scoped: TenantScopedDataSource, mock_ds: AsyncMock
    ) -> None:
        from lexigram.admin.data.query import QuerySpec

        query = QuerySpec().with_where_eq("status", "active")
        mock_ds.list.return_value = []
        await scoped.list(query)

        sent_query = mock_ds.list.await_args.args[0]
        assert query is not sent_query
        assert sent_query.to_repository_filters() == {
            "status": "active",
            "tenant_id": "tenant-acme",
        }
        assert query.to_repository_filters() == {"status": "active"}

    @pytest.mark.asyncio
    async def test_find_many_uses_canonical_scoped_query(
        self, scoped: TenantScopedDataSource, mock_ds: AsyncMock
    ) -> None:
        from lexigram.admin.data.data_source import QueryResult
        from lexigram.admin.data.query import QuerySpec

        mock_ds.find_many.return_value = QueryResult(items=[], total=0)
        await scoped.find_many(QuerySpec())

        sent_query = mock_ds.find_many.await_args.args[0]
        assert sent_query.to_repository_filters() == {"tenant_id": "tenant-acme"}

    @pytest.mark.asyncio
    async def test_find_many_filters_unscoped_backend_results(
        self, scoped: TenantScopedDataSource, mock_ds: AsyncMock
    ) -> None:
        from lexigram.admin.data.data_source import QueryResult
        from lexigram.admin.data.query import QuerySpec

        mock_ds.find_many.return_value = QueryResult(
            items=[
                {"id": "owned", "tenant_id": "tenant-acme"},
                {"id": "other", "tenant_id": "tenant-beta"},
                {"id": "unscoped"},
            ],
            total=3,
        )

        result = await scoped.find_many(QuerySpec())

        assert [item["id"] for item in result.items] == ["owned"]
        assert result.total == 3

    @pytest.mark.asyncio
    async def test_request_context_overrides_startup_fallback(
        self, scoped: TenantScopedDataSource, mock_ds: AsyncMock
    ) -> None:
        from lexigram.admin.data.query import QuerySpec
        from lexigram.admin.multitenancy.context import (
            reset_current_tenant,
            set_current_tenant,
        )

        token = set_current_tenant("tenant-beta")
        try:
            mock_ds.list.return_value = []
            await scoped.list(QuerySpec())
        finally:
            reset_current_tenant(token)

        sent_query = mock_ds.list.await_args.args[0]
        assert sent_query.to_repository_filters() == {"tenant_id": "tenant-beta"}

    @pytest.mark.asyncio
    async def test_list_injects_tenant_filter(self, scoped: TenantScopedDataSource, mock_ds: AsyncMock) -> None:
        query = _QueryWithAddFilter()
        mock_ds.list.return_value = [{"id": "record1", "tenant_id": "tenant-acme"}]
        result = await scoped.list(query)
        assert result == [{"id": "record1", "tenant_id": "tenant-acme"}]
        assert query.filters == [("tenant_id", "eq", "tenant-acme")]
        mock_ds.list.assert_awaited_once_with(query)

    @pytest.mark.asyncio
    async def test_list_graceful_without_add_filter(self, scoped: TenantScopedDataSource, mock_ds: AsyncMock) -> None:
        query = _QueryWithoutAddFilter()
        mock_ds.list.return_value = []
        result = await scoped.list(query)
        assert result == []

    # -- find_one() --

    @pytest.mark.asyncio
    async def test_find_one_returns_record_when_tenant_matches(self, scoped: TenantScopedDataSource, mock_ds: AsyncMock) -> None:
        record = MagicMock()
        record.tenant_id = "tenant-acme"
        mock_ds.find_one.return_value = record
        result = await scoped.find_one("rec-1")
        assert result is record

    @pytest.mark.asyncio
    async def test_find_one_returns_none_on_tenant_mismatch(self, scoped: TenantScopedDataSource, mock_ds: AsyncMock) -> None:
        record = MagicMock()
        record.tenant_id = "tenant-other"
        mock_ds.find_one.return_value = record
        result = await scoped.find_one("rec-1")
        assert result is None

    @pytest.mark.asyncio
    async def test_find_one_returns_none_when_not_found(self, scoped: TenantScopedDataSource, mock_ds: AsyncMock) -> None:
        mock_ds.find_one.return_value = None
        result = await scoped.find_one("rec-1")
        assert result is None

    @pytest.mark.asyncio
    async def test_find_one_handles_dict_record(self, scoped: TenantScopedDataSource, mock_ds: AsyncMock) -> None:
        mock_ds.find_one.return_value = {"id": "rec-1", "tenant_id": "tenant-acme"}
        result = await scoped.find_one("rec-1")
        assert result is not None
        assert result["tenant_id"] == "tenant-acme"

    @pytest.mark.asyncio
    async def test_find_one_dict_tenant_mismatch(self, scoped: TenantScopedDataSource, mock_ds: AsyncMock) -> None:
        mock_ds.find_one.return_value = {"id": "rec-1", "tenant_id": "tenant-other"}
        result = await scoped.find_one("rec-1")
        assert result is None

    # -- create() --

    @pytest.mark.asyncio
    async def test_create_injects_tenant_id(self, scoped: TenantScopedDataSource, mock_ds: AsyncMock) -> None:
        mock_ds.create.return_value = {"id": "new", "name": "test"}
        result = await scoped.create({"name": "test"})
        mock_ds.create.assert_awaited_once_with({"name": "test", "tenant_id": "tenant-acme"})
        assert result == {"id": "new", "name": "test"}

    @pytest.mark.asyncio
    async def test_create_overwrites_existing_tenant_id(self, scoped: TenantScopedDataSource, mock_ds: AsyncMock) -> None:
        """Tenant field is unconditionally overwritten by the scoped tenant_id."""
        mock_ds.create.return_value = {"id": "new"}
        await scoped.create({"name": "test", "tenant_id": "explicit"})
        mock_ds.create.assert_awaited_once_with(
            {"name": "test", "tenant_id": "tenant-acme"}
        )

    # -- update() / delete() --

    @pytest.mark.asyncio
    async def test_update_passthrough(self, scoped: TenantScopedDataSource, mock_ds: AsyncMock) -> None:
        mock_ds.find_one.return_value = None
        mock_ds.update.return_value = {"id": "rec-1"}
        result = await scoped.update("rec-1", {"name": "updated"})
        mock_ds.update.assert_awaited_once_with("rec-1", {"name": "updated"})
        assert result == {"id": "rec-1"}

    @pytest.mark.asyncio
    async def test_delete_passthrough(self, scoped: TenantScopedDataSource, mock_ds: AsyncMock) -> None:
        mock_ds.find_one.return_value = None
        mock_ds.delete.return_value = True
        result = await scoped.delete("rec-1")
        mock_ds.delete.assert_awaited_once_with("rec-1")
        assert result is True

    @pytest.mark.asyncio
    async def test_update_rejects_missing_tenant_metadata(
        self, scoped: TenantScopedDataSource, mock_ds: AsyncMock
    ) -> None:
        mock_ds.find_one.return_value = {"id": "rec-1", "name": "unscoped"}

        with pytest.raises(PermissionError, match="tenant scope"):
            await scoped.update("rec-1", {"name": "updated"})

        mock_ds.update.assert_not_awaited()

    # -- tenant_id property --

    def test_tenant_id_property(self, scoped: TenantScopedDataSource) -> None:
        assert scoped.tenant_id == "tenant-acme"

    # -- custom tenant_field --

    @pytest.mark.asyncio
    async def test_custom_tenant_field(self, mock_ds: AsyncMock) -> None:
        scoped = TenantScopedDataSource(mock_ds, tenant_id="org-42", tenant_field="org_id")
        query = _QueryWithAddFilter()
        await scoped.list(query)
        assert query.filters == [("org_id", "eq", "org-42")]
