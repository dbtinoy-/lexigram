"""Tests for SearchController."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.responses import HTMLResponse

from lexigram.admin.controllers.search import SearchController
from lexigram.admin.services.search_service import SearchResult, SearchResults
from lexigram.ui.core.base import render_to_string


class TestSearchController:
    """Tests for SearchController instantiation and response handling."""

    @pytest.fixture
    def mock_service(self) -> MagicMock:
        service = MagicMock()
        service.search = AsyncMock()
        return service

    def test_can_instantiate(self, mock_service: MagicMock) -> None:
        controller = SearchController(search_service=mock_service)
        assert controller._search_service is mock_service

    @pytest.mark.asyncio
    async def test_search_returns_html_response(self, mock_service: MagicMock) -> None:
        mock_service.search.return_value = SearchResults(query="test")
        controller = SearchController(search_service=mock_service)
        request = MagicMock()
        request.query_params = {"q": "test"}
        response = await controller.search(request)
        assert isinstance(response, HTMLResponse)

    @pytest.mark.asyncio
    async def test_search_uses_q_param(self, mock_service: MagicMock) -> None:
        mock_service.search.return_value = SearchResults(query="alice")
        controller = SearchController(search_service=mock_service)
        request = MagicMock()
        request.query_params = {"q": "alice"}
        await controller.search(request)
        mock_service.search.assert_awaited_once_with("alice", rule=None)

    @pytest.mark.asyncio
    async def test_search_uses_search_param_fallback(
        self, mock_service: MagicMock
    ) -> None:
        mock_service.search.return_value = SearchResults(query="bob")
        controller = SearchController(search_service=mock_service)
        request = MagicMock()
        request.query_params = {"search": "bob"}
        await controller.search(request)
        mock_service.search.assert_awaited_once_with("bob", rule=None)

    @pytest.mark.asyncio
    async def test_search_uses_q_over_search_param(
        self, mock_service: MagicMock
    ) -> None:
        mock_service.search.return_value = SearchResults(query="qval")
        controller = SearchController(search_service=mock_service)
        request = MagicMock()
        request.query_params = {"q": "qval", "search": "sval"}
        await controller.search(request)
        mock_service.search.assert_awaited_once_with("qval", rule=None)

    @pytest.mark.asyncio
    async def test_search_forwards_rule_param(self, mock_service: MagicMock) -> None:
        """The block-JSON rule is forwarded to SearchService.search."""
        rule = (
            '{"logic":"AND","rules":[{"field":"role","operator":"eq","value":"admin"}]}'
        )
        mock_service.search.return_value = SearchResults(query="t")
        controller = SearchController(search_service=mock_service)
        request = MagicMock()
        request.query_params = {"q": "t", "rule": rule}
        await controller.search(request)
        mock_service.search.assert_awaited_once_with("t", rule=rule)

    @pytest.mark.asyncio
    async def test_search_empty_query_returns_no_results_html(
        self, mock_service: MagicMock
    ) -> None:
        mock_service.search.return_value = SearchResults(query="")
        controller = SearchController(search_service=mock_service)
        request = MagicMock()
        request.query_params = {}
        response = await controller.search(request)
        content = response.body.decode()
        assert "No results found" in content

    @pytest.mark.asyncio
    async def test_search_htmx_request_returns_fragment_only(
        self, mock_service: MagicMock
    ) -> None:
        """HTMX requests keep the fragment-only contract (header drop-down)."""
        mock_service.search.return_value = SearchResults(query="test")
        controller = SearchController(search_service=mock_service)
        request = MagicMock()
        request.query_params = {"q": "test"}
        request.headers.get.return_value = "true"
        response = await controller.search(request)
        content = response.body.decode()
        assert "No results found" in content
        assert "Global Search" not in content

    @pytest.mark.asyncio
    async def test_search_direct_navigation_returns_full_page(
        self, mock_service: MagicMock
    ) -> None:
        """Direct navigation renders the search page inside the admin shell."""
        mock_service.search.return_value = SearchResults(query="alice")
        mock_service.get_search_field_catalog = MagicMock(return_value=[])
        controller = SearchController(search_service=mock_service)
        request = MagicMock()
        request.query_params = {"q": "alice"}
        request.headers.get.return_value = None
        response = await controller.search(request)
        content = response.body.decode()
        assert "Global Search" in content
        assert 'id="search-results"' in content
        assert 'name="q"' in content

    @pytest.mark.asyncio
    async def test_search_full_page_embeds_query_builder(
        self, mock_service: MagicMock
    ) -> None:
        """The full page embeds the query-builder rule input in the search form."""
        mock_service.search.return_value = SearchResults(query="alice")
        mock_service.get_search_field_catalog = MagicMock(
            return_value=[{"name": "role", "label": "Role"}]
        )
        controller = SearchController(search_service=mock_service)
        request = MagicMock()
        request.query_params = {"q": "alice"}
        request.headers.get.return_value = None
        response = await controller.search(request)
        content = response.body.decode()
        assert 'id="search-form"' in content
        assert 'name="rule"' in content
        assert "Role" in content

    @pytest.mark.asyncio
    async def test_search_page_rule_round_trips_into_builder(
        self, mock_service: MagicMock
    ) -> None:
        """A submitted rule is pre-loaded into the page's query builder."""
        rule = (
            '{"logic":"AND","rules":[{"field":"role","operator":"eq","value":"admin"}]}'
        )
        mock_service.search.return_value = SearchResults(query="alice")
        mock_service.get_search_field_catalog = MagicMock(return_value=[])
        controller = SearchController(search_service=mock_service)
        request = MagicMock()
        request.query_params = {"q": "alice", "rule": rule}
        request.headers.get.return_value = None
        response = await controller.search(request)
        content = response.body.decode()
        assert "admin" in content

    @pytest.mark.asyncio
    async def test_search_full_page_embeds_initial_results(
        self, mock_service: MagicMock
    ) -> None:
        """The full page pre-renders the current query's results server-side."""
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
        request.headers.get.return_value = None
        response = await controller.search(request)
        content = response.body.decode()
        assert "Alice" in content
        assert "/admin/users/1" in content


class TestSearchControllerRender:
    """Tests for _render_results output."""

    @pytest.fixture
    def controller(self) -> SearchController:
        service = MagicMock()
        return SearchController(search_service=service)

    def test_render_no_results(self, controller: SearchController) -> None:
        results = SearchResults(query="test", total_count=0)
        html = render_to_string(controller._render_results(results))
        assert "No results found" in html
        assert "search-results-empty" in html

    def test_render_with_results_groups_by_resource(
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
        html = render_to_string(controller._render_results(results))
        assert "search-results" in html
        assert "search-resource-group" in html
        assert "Users" in html
        assert "Posts" in html
        assert "Alice" in html
        assert "Hello World" in html
        assert "alice@example.com" in html
        assert "/admin/users/1" in html
        assert "/admin/posts/10" in html

    def test_render_subtitle_omitted_when_empty(
        self, controller: SearchController
    ) -> None:
        results = SearchResults(
            query="test",
            total_count=1,
            resource_counts={"posts": 1},
            results=[
                SearchResult(
                    resource_name="posts",
                    resource_label="Posts",
                    id=10,
                    title="Hello World",
                    subtitle="",
                    url="/admin/posts/10",
                ),
            ],
        )
        html = render_to_string(controller._render_results(results))
        assert "search-subtitle" not in html

    def test_render_subtitle_included_when_present(
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
                    subtitle="alice@example.com",
                    url="/admin/users/1",
                ),
            ],
        )
        html = render_to_string(controller._render_results(results))
        assert 'class="search-subtitle"' in html
        assert "alice@example.com" in html

    def test_render_hx_attributes_on_result_links(
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
        html = render_to_string(controller._render_results(results))
        assert 'hx-get="/admin/users/1"' in html
        assert 'hx-target="body"' in html
        assert 'hx-push-url="true"' in html

    def test_render_single_resource_no_group_header(
        self, controller: SearchController
    ) -> None:
        """Single result should not produce multiple groups."""
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
        html = render_to_string(controller._render_results(results))
        assert html.count("search-resource-group") == 1


class TestSearchHostileData:
    """Regression tests: hostile result fields are escaped on both transports."""

    HOSTILE_TEXT = '<script>alert("xss")</script>'
    HOSTILE_URL = '"><img src=x onerror=alert(1)>'

    @pytest.fixture
    def mock_service(self) -> MagicMock:
        service = MagicMock()
        service.search = AsyncMock()
        return service

    def _hostile_results(self) -> SearchResults:
        return SearchResults(
            query="x",
            total_count=1,
            resource_counts={"users": 1},
            results=[
                SearchResult(
                    resource_name="users",
                    resource_label=self.HOSTILE_TEXT,
                    id=1,
                    title=self.HOSTILE_TEXT,
                    subtitle=self.HOSTILE_TEXT,
                    url=self.HOSTILE_URL,
                ),
            ],
        )

    @pytest.mark.asyncio
    async def test_htmx_fragment_escapes_hostile_fields(
        self, mock_service: MagicMock
    ) -> None:
        """The HTMX fragment must never emit raw script or markup."""
        mock_service.search.return_value = self._hostile_results()
        controller = SearchController(search_service=mock_service)
        request = MagicMock()
        request.query_params = {"q": "x"}
        request.headers.get.return_value = "true"
        response = await controller.search(request)
        content = response.body.decode()
        assert "<script>" not in content
        assert "<img" not in content
        assert "&lt;script&gt;" in content
        assert '&lt;script&gt;alert("xss")&lt;/script&gt;' in content
        assert "&quot;&gt;&lt;img src=x onerror=alert(1)&gt;" in content

    @pytest.mark.asyncio
    async def test_full_page_escapes_hostile_fields_once(
        self, mock_service: MagicMock
    ) -> None:
        """Full page: escaped exactly once (no fragment double-escape)."""
        mock_service.search.return_value = self._hostile_results()
        mock_service.get_search_field_catalog = MagicMock(return_value=[])
        controller = SearchController(search_service=mock_service)
        request = MagicMock()
        request.query_params = {"q": "x"}
        request.headers.get.return_value = None
        response = await controller.search(request)
        content = response.body.decode()
        start = content.index('id="search-results"')
        end = content.index("<script>", start)
        region = content[start:end]
        assert "<script>" not in region
        assert "<img" not in region
        assert "&lt;script&gt;" in region
        assert '&lt;script&gt;alert("xss")&lt;/script&gt;' in region
        assert "&quot;&gt;&lt;img src=x onerror=alert(1)&gt;" in region
        assert "&amp;lt;script&amp;gt;" not in region
