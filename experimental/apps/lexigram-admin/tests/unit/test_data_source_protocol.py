"""Tests for IDataSource protocol enforcement (Phase 6)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from lexigram.admin.data.data_source import IDataSource, QueryResult


class TestIDataSourceProtocol:
    """IDataSource is @runtime_checkable and validates implementations."""

    def test_is_runtime_checkable(self) -> None:
        """IDataSource should be runtime-checkable."""
        assert hasattr(IDataSource, "__instancecheck__")

    def test_apidata_source_is_valid(self) -> None:
        """APIDataSource should satisfy isinstance check against IDataSource."""
        from lexigram.admin.data.adapters.api_adapter import APIDataSource

        try:
            ds: APIDataSource[Any] = APIDataSource(base_url="http://test.local")
            assert isinstance(ds, IDataSource)
        except ImportError:
            pytest.skip("httpx not installed")

    def test_inmemory_data_source_is_valid(self) -> None:
        """InMemoryDataSource should satisfy isinstance check against IDataSource."""
        from lexigram.admin.data.adapters.memory_adapter import InMemoryDataSource

        ds: InMemoryDataSource[Any] = InMemoryDataSource(data=[])
        assert isinstance(ds, IDataSource)

    def test_repository_adapter_is_valid(self) -> None:
        """RepositoryDataSource (adapters.repository) should satisfy isinstance."""
        from lexigram.admin.data.adapters.repository import RepositoryDataSource
        from lexigram.contracts.admin.repository import AdminRepositoryProtocol

        mock_repo = AsyncMock(spec=AdminRepositoryProtocol)
        ds: RepositoryDataSource[Any] = RepositoryDataSource(repository=mock_repo)
        assert isinstance(ds, IDataSource)

    def test_plain_object_not_idata_source(self) -> None:
        """A plain object should NOT pass isinstance check."""

        class NotADataSource:
            pass

        assert not isinstance(NotADataSource(), IDataSource)

    def test_partial_implementation_fails_check(self) -> None:
        """An object missing required methods should NOT pass isinstance."""

        class PartialDataSource:
            async def find_many(self, query: Any) -> QueryResult[Any]:  # noqa: ARG002
                return QueryResult(items=[])

            # Missing find_one, count, create, update, delete, bulk_*

        assert not isinstance(PartialDataSource(), IDataSource)


class TestIDataSourceProtocolMethods:
    """Verify method signatures exist on IDataSource protocol."""

    def test_all_crud_methods_present(self) -> None:
        """Check that IDataSource has all required CRUD methods."""
        methods = [
            "find_many",
            "find_one",
            "count",
            "create",
            "update",
            "delete",
            "bulk_create",
            "bulk_update",
            "bulk_delete",
        ]
        for name in methods:
            assert hasattr(IDataSource, name), f"IDataSource missing method: {name}"


class TestSetDataSourceEnforcement:
    """Resource.set_data_source() should enforce IDataSource protocol."""

    def test_valid_data_source_accepted(self) -> None:
        """set_data_source should accept an IDataSource-compatible object."""
        from lexigram.admin.data.adapters.memory_adapter import InMemoryDataSource
        from lexigram.admin.resources.base import Resource

        resource = Resource()
        ds: InMemoryDataSource[Any] = InMemoryDataSource(data=[])
        resource.set_data_source(ds)
        assert resource._data_source is ds

    def test_invalid_data_source_rejected(self) -> None:
        """set_data_source should raise TypeError for non-IDataSource."""
        from lexigram.admin.resources.base import Resource

        resource = Resource()

        class NotIDataSource:
            pass

        with pytest.raises(TypeError, match="data_source must implement IDataSource"):
            resource.set_data_source(NotIDataSource())  # type: ignore[arg-type]

    def test_none_data_source_rejected(self) -> None:
        """set_data_source should raise TypeError for None."""
        from lexigram.admin.resources.base import Resource

        resource = Resource()
        with pytest.raises(TypeError, match="data_source must implement IDataSource"):
            resource.set_data_source(None)  # type: ignore[arg-type]


class TestResourceFetchList:
    """Resource.fetch_list() delegates to _data_source.find_many()."""

    @pytest.mark.asyncio
    async def test_fetch_list_returns_empty_when_no_data_source(self) -> None:
        """fetch_list should return empty tuple when _data_source is None."""
        from lexigram.admin.resources.base import Resource

        resource = Resource()
        items, total = await resource.fetch_list()
        assert items == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_fetch_list_delegates_to_find_many(self) -> None:
        """fetch_list should call _data_source.find_many with a Query."""
        from lexigram.admin.data.adapters.memory_adapter import InMemoryDataSource
        from lexigram.admin.resources.base import Resource

        resource = Resource()
        ds: InMemoryDataSource[Any] = InMemoryDataSource(
            data=[{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]
        )
        resource.set_data_source(ds)

        items, total = await resource.fetch_list(
            limit=10,
            offset=0,
            filters={"name": "A"},
            sort_by="id",
            sort_order="asc",
        )
        assert total == 1
        assert len(items) == 1

    @pytest.mark.asyncio
    async def test_fetch_list_with_search(self) -> None:
        """fetch_list should pass search parameters to QueryBuilder."""
        from lexigram.admin.data.adapters.memory_adapter import InMemoryDataSource
        from lexigram.admin.resources.base import Resource

        resource = Resource()
        ds: InMemoryDataSource[Any] = InMemoryDataSource(
            data=[
                {"id": 1, "name": "Alpha"},
                {"id": 2, "name": "Beta"},
                {"id": 3, "name": "Gamma"},
            ]
        )
        resource.set_data_source(ds)

        items, total = await resource.fetch_list(
            limit=10,
            offset=0,
            search="Beta",
            search_fields=["name"],
        )
        assert total == 1
        assert items[0]["name"] == "Beta"

    @pytest.mark.asyncio
    async def test_fetch_list_with_pagination(self) -> None:
        """fetch_list should paginate correctly."""
        from lexigram.admin.data.adapters.memory_adapter import InMemoryDataSource
        from lexigram.admin.resources.base import Resource

        resource = Resource()
        ds: InMemoryDataSource[Any] = InMemoryDataSource(
            data=[
                {"id": 1, "name": "A"},
                {"id": 2, "name": "B"},
                {"id": 3, "name": "C"},
            ]
        )
        resource.set_data_source(ds)

        # Page 1: limit=2, offset=0 -> items 0-1
        items_p1, total = await resource.fetch_list(limit=2, offset=0)
        assert len(items_p1) == 2
        assert total == 3

        # Page 2: limit=2, offset=2 -> items 2-2
        items_p2, total = await resource.fetch_list(limit=2, offset=2)
        assert len(items_p2) == 1
        assert total == 3


class TestDataSourceImplementations:
    """Verify that all IDataSource implementations pass isinstance check."""

    def test_sql_data_source_is_not_runtime_checkable(self) -> None:
        """SqlDataSource extends ABC, not Protocol — not runtime-checkable."""
        from lexigram.admin.data.data_source import SqlDataSource

        assert not issubclass(SqlDataSource, IDataSource)

    def test_data_source_base_not_idata_source(self) -> None:
        """DataSourceBase is ABC, not IDataSource."""
        from lexigram.admin.data.data_source import DataSourceBase

        assert not issubclass(DataSourceBase, IDataSource)
