"""Tests for the search results UI rendering.

Verifies the HTML structure produced by SearchController._render_results
has the expected CSS classes, Tailwind utility classes, and structural
elements that the frontend depends on.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.responses import HTMLResponse

from lexigram.admin.controllers.search import SearchController
from lexigram.admin.services.search_service import SearchResult, SearchResults


class TestSearchResultsHTMLStructure:
    """Tests for the HTML structure of rendered search results."""

    @pytest.fixture
    def controller(self) -> SearchController:
        return SearchController(search_service=MagicMock())

    def test_empty_results_has_expected_classes(
        self, controller: SearchController
    ) -> None:
        results = SearchResults(query="test", total_count=0)
        html = controller._render_results(results)
        assert 'class="search-results-empty' in html
        assert "No results found" in html

    def populated_results(self) -> SearchResults:
        return SearchResults(
            query="test",
            total_count=2,
            resource_counts={"users": 1, "posts": 1},
            results=[
                SearchResult(
                    resource_name="users",
                    resource_label="Users",
                    id=1,
                    title="Alice",
                    subtitle="alice@example.com",
                    url="/admin/users/1",
                ),
                SearchResult(
                    resource_name="posts",
                    resource_label="Posts",
                    id=10,
                    title="Hello World",
                    url="/admin/posts/10",
                ),
            ],
        )

    def test_populated_results_wrapper_classes(
        self, controller: SearchController
    ) -> None:
        html = controller._render_results(self.populated_results())
        assert 'class="search-results' in html
        assert "rounded-xl" in html
        assert "shadow-lg" in html
        assert "bg-card" in html

    def test_resource_group_has_divider_classes(
        self, controller: SearchController
    ) -> None:
        html = controller._render_results(self.populated_results())
        assert 'class="search-resource-group' in html
        assert "border-b" in html

    def test_resource_header_has_styled_classes(
        self, controller: SearchController
    ) -> None:
        html = controller._render_results(self.populated_results())
        assert 'class="search-resource-header' in html
        assert "uppercase" in html
        assert "tracking-wider" in html

    def test_result_item_has_interactive_classes(
        self, controller: SearchController
    ) -> None:
        html = controller._render_results(self.populated_results())
        assert 'class="search-result-item' in html
        assert "hover:bg-muted" in html
        assert "focus:outline-none" in html
        assert "transition-colors" in html

    def test_result_title_has_typography_classes(
        self, controller: SearchController
    ) -> None:
        html = controller._render_results(self.populated_results())
        assert 'class="search-result-title' in html
        assert "text-sm" in html
        assert "font-medium" in html

    def test_result_resource_label_has_styled_classes(
        self, controller: SearchController
    ) -> None:
        html = controller._render_results(self.populated_results())
        assert 'class="search-result-resource' in html
        assert "text-xs" in html
        assert "text-muted-foreground" in html

    def test_subtitle_has_block_classes_when_present(
        self, controller: SearchController
    ) -> None:
        html = controller._render_results(self.populated_results())
        assert 'class="search-subtitle' in html
        assert "block" in html
        assert "text-xs" in html

    def test_dark_mode_classes_present(
        self, controller: SearchController
    ) -> None:
        html = controller._render_results(self.populated_results())
        assert "dark:" in html


class TestSearchResultsVisualStates:
    """Tests that populated and empty results look different."""

    @pytest.fixture
    def controller(self) -> SearchController:
        return SearchController(search_service=MagicMock())

    def test_empty_has_no_groups(self, controller: SearchController) -> None:
        empty = SearchResults(query="test", total_count=0)
        html = controller._render_results(empty)
        assert "search-resource-group" not in html
        assert "search-results-empty" in html

    def test_populated_has_no_empty_text(
        self, controller: SearchController
    ) -> None:
        results = SearchResults(
            query="test",
            total_count=1,
            resource_counts={"users": 1},
            results=[
                SearchResult(
                    resource_name="users",
                    resource_label="Users",
                    id=1,
                    title="Alice",
                    url="/admin/users/1",
                ),
            ],
        )
        html = controller._render_results(results)
        assert "No results found" not in html
        assert "search-results-empty" not in html
        assert "search-results" in html

    def test_populated_has_resource_groups(
        self, controller: SearchController
    ) -> None:
        results = SearchResults(
            query="test",
            total_count=2,
            resource_counts={"users": 1, "posts": 1},
            results=[
                SearchResult(
                    resource_name="users",
                    resource_label="Users",
                    id=1,
                    title="Alice",
                    url="/admin/users/1",
                ),
                SearchResult(
                    resource_name="posts",
                    resource_label="Posts",
                    id=10,
                    title="Hello World",
                    url="/admin/posts/10",
                ),
            ],
        )
        html = controller._render_results(results)
        assert html.count("search-resource-group") == 2
        assert "Users" in html
        assert "Posts" in html


class TestSearchControllerIntegration:
    """Tests for controller-level integration with the search service."""

    @pytest.mark.asyncio
    async def test_search_service_invoked_with_query(self) -> None:
        mock_service = MagicMock()
        mock_service.search = AsyncMock()
        mock_service.search.return_value = SearchResults(
            query="alice",
            total_count=1,
            resource_counts={"users": 1},
            results=[
                SearchResult(
                    resource_name="users",
                    resource_label="Users",
                    id=1,
                    title="Alice",
                    url="/admin/users/1",
                ),
            ],
        )

        controller = SearchController(search_service=mock_service)
        request = MagicMock()
        request.query_params = {"q": "alice"}
        response = await controller.search(request)
        mock_service.search.assert_awaited_once_with("alice", rule=None)
        content = response.body.decode()
        assert 'class="search-results' in content
        assert "Alice" in content

    @pytest.mark.asyncio
    async def test_search_empty_via_service_returns_empty_html(self) -> None:
        mock_service = MagicMock()
        mock_service.search = AsyncMock()
        mock_service.search.return_value = SearchResults(query="")

        controller = SearchController(search_service=mock_service)
        request = MagicMock()
        request.query_params = {"q": ""}
        response = await controller.search(request)
        content = response.body.decode()
        assert "No results found" in content
        assert "search-results-empty" in content

    @pytest.mark.asyncio
    async def test_controller_returns_html_response(self) -> None:
        mock_service = MagicMock()
        mock_service.search = AsyncMock()
        mock_service.search.return_value = SearchResults(query="test")

        controller = SearchController(search_service=mock_service)
        request = MagicMock()
        request.query_params = {"q": "test"}
        response = await controller.search(request)
        assert isinstance(response, HTMLResponse)
