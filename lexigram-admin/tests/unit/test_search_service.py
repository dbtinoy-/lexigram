"""Tests for the global search service."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from lexigram.admin.services.search_service import (
    SearchResult,
    SearchResults,
    SearchService,
)


class MockResource1:
    name = "users"
    label = "Users"
    search_fields = ["name", "email"]

    @classmethod
    async def search(cls, query: str, *, limit: int = 5) -> list[dict]:
        return [{"id": 1, "title": "Alice", "subtitle": "alice@example.com"}]


class MockResource2:
    name = "posts"
    label = "Posts"
    search_fields = ["title"]

    @classmethod
    async def search(cls, query: str, *, limit: int = 5) -> list[dict]:
        return [{"id": 10, "title": "Hello World"}]


class MockResourceNoSearch:
    name = "logs"
    label = "Logs"
    search_fields = []


class TestSearchResultDataclass:
    """Tests for the SearchResult dataclass."""

    def test_fields(self) -> None:
        result = SearchResult(
            resource_name="users",
            resource_label="Users",
            id=1,
            title="Alice",
            subtitle="alice@example.com",
            url="/admin/users/1",
        )
        assert result.resource_name == "users"
        assert result.resource_label == "Users"
        assert result.id == 1
        assert result.title == "Alice"
        assert result.subtitle == "alice@example.com"
        assert result.url == "/admin/users/1"

    def test_defaults(self) -> None:
        result = SearchResult(
            resource_name="users",
            resource_label="Users",
            id=1,
            title="Alice",
        )
        assert result.subtitle == ""
        assert result.url == ""


class TestSearchResultsDataclass:
    """Tests for the SearchResults dataclass."""

    def test_has_results_true(self) -> None:
        results = SearchResults(query="test", total_count=3)
        assert results.has_results is True

    def test_has_results_false(self) -> None:
        results = SearchResults(query="test", total_count=0)
        assert results.has_results is False

    def test_group_count_matches_resource_counts(self) -> None:
        results = SearchResults(
            query="test",
            total_count=3,
            resource_counts={"users": 2, "posts": 1},
        )
        assert results.group_count == 2

    def test_group_count_empty(self) -> None:
        results = SearchResults(query="test")
        assert results.group_count == 0


class TestSearchService:
    """Tests for the SearchService."""

    @pytest.fixture
    def mock_manager(self) -> MagicMock:
        manager = MagicMock()
        manager.get_all_resources = MagicMock(
            return_value=[MockResource1, MockResource2, MockResourceNoSearch]
        )
        return manager

    @pytest.fixture
    def service(self, mock_manager: MagicMock) -> SearchService:
        return SearchService(resource_manager=mock_manager)

    def test_initializes_with_resource_manager(self, mock_manager: MagicMock) -> None:
        service = SearchService(resource_manager=mock_manager)
        assert service._resource_manager is mock_manager

    async def test_search_empty_query_returns_empty(
        self, service: SearchService
    ) -> None:
        result = await service.search("")
        assert result.total_count == 0
        assert result.results == []
        assert result.has_results is False

    async def test_search_blank_query_returns_empty(
        self, service: SearchService
    ) -> None:
        result = await service.search("   ")
        assert result.total_count == 0
        assert result.has_results is False

    async def test_search_calls_search_on_searchable_resources(
        self, service: SearchService
    ) -> None:
        result = await service.search("alice")
        assert result.total_count == 2
        assert result.resource_counts.get("users") == 1
        assert result.resource_counts.get("posts") == 1

    async def test_search_skips_resources_without_search_fields(
        self, mock_manager: MagicMock
    ) -> None:
        service = SearchService(resource_manager=mock_manager)
        resources = service.get_searchable_resources()
        names = [r.name for r in resources]
        assert "logs" not in names
        assert "users" in names
        assert "posts" in names

    async def test_search_aggregates_results_from_multiple_resources(
        self, service: SearchService
    ) -> None:
        result = await service.search("test")
        assert result.total_count == 2
        assert len(result.results) == 2
        assert result.results[0].resource_name == "users"
        assert result.results[1].resource_name == "posts"

    async def test_search_handles_resource_errors_gracefully(
        self, mock_manager: MagicMock
    ) -> None:
        class FailingResource:
            name = "failing"
            label = "Failing"
            search_fields = ["name"]

            @classmethod
            async def search(cls, query: str, *, limit: int = 5) -> list[dict]:
                raise RuntimeError("Search failed")

        mock_manager.get_all_resources = MagicMock(
            return_value=[MockResource1, FailingResource, MockResource2]
        )
        service = SearchService(resource_manager=mock_manager)

        result = await service.search("test")
        assert result.total_count == 2
        assert result.results[0].resource_name == "users"
        assert result.results[1].resource_name == "posts"

    async def test_search_respects_per_resource_limit(
        self, mock_manager: MagicMock
    ) -> None:
        class ManyResultsResource:
            name = "items"
            label = "Items"
            search_fields = ["name"]

            @classmethod
            async def search(cls, query: str, *, limit: int = 5) -> list[dict]:
                return [{"id": i, "title": f"Item {i}"} for i in range(limit)]

        mock_manager.get_all_resources = MagicMock(return_value=[ManyResultsResource])
        service = SearchService(resource_manager=mock_manager)

        result = await service.search("test", per_resource=3)
        assert result.total_count == 3
        assert len(result.results) == 3

    async def test_get_searchable_resources_returns_only_with_search_fields(
        self, mock_manager: MagicMock
    ) -> None:
        service = SearchService(resource_manager=mock_manager)
        resources = service.get_searchable_resources()
        assert len(resources) == 2
        assert MockResource1 in resources
        assert MockResource2 in resources
        assert MockResourceNoSearch not in resources
