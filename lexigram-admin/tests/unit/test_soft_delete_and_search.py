"""Tests for soft delete support and global search enhancements."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.admin.data.query import QuerySpec


class TestQuerySpecIncludeDeleted:
    """Tests for the include_deleted flag on QuerySpec."""

    def test_default_excludes_deleted(self) -> None:
        q = QuerySpec()
        assert q.include_deleted is False

    def test_with_deleted_sets_flag(self) -> None:
        q = QuerySpec().with_deleted()
        assert q.include_deleted is True

    def test_with_deleted_false_clears_flag(self) -> None:
        q = QuerySpec(include_deleted=True).with_deleted(False)
        assert q.include_deleted is False

    def test_with_page_propagates_include_deleted(self) -> None:
        q = QuerySpec(include_deleted=True).with_page(2)
        assert q.include_deleted is True

    def test_with_filters_propagates_include_deleted(self) -> None:
        q = QuerySpec(include_deleted=True).with_filters(status="active")
        assert q.include_deleted is True

    def test_with_sort_propagates_include_deleted(self) -> None:
        q = QuerySpec(include_deleted=True).with_sort("name")
        assert q.include_deleted is True

    def test_with_search_propagates_include_deleted(self) -> None:
        q = QuerySpec(include_deleted=True).with_search("foo", fields=["name"])
        assert q.include_deleted is True

    def test_with_include_propagates_include_deleted(self) -> None:
        q = QuerySpec(include_deleted=True).with_include("tags")
        assert q.include_deleted is True

    def test_from_dict_reads_include_deleted(self) -> None:
        q = QuerySpec.from_dict({"include_deleted": True})
        assert q.include_deleted is True

    def test_from_dict_defaults_false(self) -> None:
        q = QuerySpec.from_dict({})
        assert q.include_deleted is False

    def test_to_dict_includes_flag_when_true(self) -> None:
        d = QuerySpec(include_deleted=True).to_dict()
        assert d["include_deleted"] is True

    def test_to_dict_omits_flag_when_false(self) -> None:
        d = QuerySpec().to_dict()
        assert "include_deleted" not in d


class TestRepositoryDataSourceSoftDelete:
    """Tests for RepositoryDataSource filter passing."""

    def _make_repo(self) -> MagicMock:
        repo = MagicMock()
        repo.find_by_id = AsyncMock(return_value=None)
        repo.find_many = AsyncMock(return_value=[])
        repo.count = AsyncMock(return_value=0)
        repo.create = AsyncMock()
        repo.update = AsyncMock()
        repo.delete = AsyncMock(return_value=True)
        return repo

    @pytest.mark.asyncio
    async def test_passes_filters_to_repository(self) -> None:
        from lexigram.admin.data.adapters.repository import RepositoryDataSource

        repo = self._make_repo()
        ds: RepositoryDataSource[Any] = RepositoryDataSource(repo)

        q = QuerySpec().with_filters(status="active")
        await ds.find_many(q)

        call_kwargs = repo.find_many.call_args.kwargs
        assert call_kwargs.get("filters") is not None

    @pytest.mark.asyncio
    async def test_includes_search_params(self) -> None:
        from lexigram.admin.data.adapters.repository import RepositoryDataSource

        repo = self._make_repo()
        ds: RepositoryDataSource[Any] = RepositoryDataSource(repo)

        q = QuerySpec().with_search("foo", fields=["name"])
        await ds.find_many(q)

        call_kwargs = repo.find_many.call_args.kwargs
        assert call_kwargs.get("search") == "foo"
        assert call_kwargs.get("search_fields") == ["name"]

    @pytest.mark.asyncio
    async def test_passes_sort_params(self) -> None:
        from lexigram.admin.data.adapters.repository import RepositoryDataSource

        repo = self._make_repo()
        ds: RepositoryDataSource[Any] = RepositoryDataSource(repo)

        q = QuerySpec().with_sort("name", order="asc")
        await ds.find_many(q)

        call_kwargs = repo.find_many.call_args.kwargs
        assert call_kwargs.get("order_by") is not None


class TestResourceSearch:
    """Tests for Resource.search() default implementation."""

    @pytest.mark.asyncio
    async def test_search_empty_when_no_search_fields(self) -> None:
        from lexigram.admin.resources.base import Resource

        resource = Resource()
        resource._data_source = MagicMock()
        results = await resource.search("test")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_empty_when_no_data_source(self) -> None:
        from lexigram.admin.resources.base import Resource

        resource = Resource()
        resource.search_fields = ["name"]
        results = await resource.search("test")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_returns_hits(self) -> None:
        from lexigram.admin.resources.base import Resource

        resource = Resource()
        resource.search_fields = ["name", "email"]
        resource.search_title_field = "name"

        mock_ds = MagicMock()
        mock_result = MagicMock()
        mock_result.items = [
            {"id": "1", "name": "Alice", "email": "alice@example.com"},
            {"id": "2", "name": "Bob", "email": "bob@example.com"},
        ]
        mock_ds.find_many = AsyncMock(return_value=mock_result)
        resource._data_source = mock_ds

        hits = await resource.search("alice", limit=5)

        assert len(hits) == 2
        assert hits[0]["id"] == "1"
        assert hits[0]["title"] == "Alice"
        assert hits[0]["subtitle"] == "alice@example.com"

    @pytest.mark.asyncio
    async def test_search_handles_object_items(self) -> None:
        from lexigram.admin.resources.base import Resource

        resource = Resource()
        resource.search_fields = ["name"]
        resource.search_title_field = "name"

        item = MagicMock()
        item.id = "42"
        item.name = "Carol"
        item.email = "carol@example.com"
        item.description = ""

        mock_ds = MagicMock()
        mock_result = MagicMock()
        mock_result.items = [item]
        mock_ds.find_many = AsyncMock(return_value=mock_result)
        resource._data_source = mock_ds

        hits = await resource.search("carol")

        assert hits[0]["id"] == "42"
        assert hits[0]["title"] == "Carol"
