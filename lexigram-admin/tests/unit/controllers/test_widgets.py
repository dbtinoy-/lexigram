"""Tests for WidgetController routing logic."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.routing import Route

from lexigram.admin.controllers.widgets import WidgetController
from lexigram.contracts.admin.types import WidgetViewModel
from lexigram.result import Err, Ok


class TestWidgetController:
    @pytest.fixture
    def mock_registry(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def mock_contributor(self) -> MagicMock:
        return MagicMock()

    @pytest.mark.asyncio
    async def test_returns_200_with_error_card_when_contributor_not_found(
        self, mock_registry: MagicMock
    ) -> None:
        mock_registry.get.return_value = None
        controller = WidgetController(registry=mock_registry)
        mock_request = MagicMock()
        mock_request.query_params = {}
        response = await controller.render_widget(
            request=mock_request,
            contributor_id="nonexistent",
            widget_name="some_widget",
        )
        assert response.status_code == 200
        assert b"widget-error-card" in response.body
        assert b"Contributor" in response.body

    @pytest.mark.asyncio
    async def test_returns_html_on_ok_result(
        self, mock_registry: MagicMock, mock_contributor: MagicMock
    ) -> None:
        mock_registry.get.return_value = mock_contributor
        mock_contributor.render_widget = AsyncMock(
            return_value=Ok(WidgetViewModel(body="<div>ok</div>"))
        )
        controller = WidgetController(registry=mock_registry)
        mock_request = MagicMock()
        mock_request.query_params = {}
        response = await controller.render_widget(
            request=mock_request,
            contributor_id="sql",
            widget_name="pool_utilization",
        )
        assert response.status_code == 200
        assert b"<div>ok</div>" in response.body

    @pytest.mark.asyncio
    async def test_returns_200_with_error_card_on_widget_not_found(
        self, mock_registry: MagicMock, mock_contributor: MagicMock
    ) -> None:
        from lexigram.contracts.admin.errors import WidgetNotFoundError

        mock_registry.get.return_value = mock_contributor
        mock_contributor.render_widget = AsyncMock(
            return_value=Err(WidgetNotFoundError("sql", "unknown_widget"))
        )
        controller = WidgetController(registry=mock_registry)
        mock_request = MagicMock()
        mock_request.query_params = {}
        response = await controller.render_widget(
            request=mock_request,
            contributor_id="sql",
            widget_name="unknown_widget",
        )
        assert response.status_code == 200
        assert b"widget-error-card" in response.body

    @pytest.mark.asyncio
    async def test_returns_200_with_error_card_on_domain_error(
        self, mock_registry: MagicMock, mock_contributor: MagicMock
    ) -> None:
        from lexigram.contracts.admin.errors import AdminError

        mock_registry.get.return_value = mock_contributor
        mock_contributor.render_widget = AsyncMock(
            return_value=Err(AdminError("data unavailable"))
        )
        controller = WidgetController(registry=mock_registry)
        mock_request = MagicMock()
        mock_request.query_params = {}
        response = await controller.render_widget(
            request=mock_request,
            contributor_id="sql",
            widget_name="pool_utilization",
        )
        assert response.status_code == 200
        assert b"widget-error-card" in response.body


class TestWidgetControllerGetRoutes:
    """Tests for WidgetController.get_routes() method."""

    @pytest.fixture
    def mock_registry(self) -> MagicMock:
        return MagicMock()

    def test_get_routes_returns_list(self, mock_registry: MagicMock) -> None:
        """Test that get_routes returns a list."""
        controller = WidgetController(registry=mock_registry)
        routes = controller.get_routes()
        assert isinstance(routes, list)

    def test_get_routes_returns_starlette_routes(self, mock_registry: MagicMock) -> None:
        """Test that get_routes returns Starlette Route objects."""
        controller = WidgetController(registry=mock_registry)
        routes = controller.get_routes()
        for route in routes:
            assert isinstance(route, Route)

    def test_get_routes_includes_widget_route(self, mock_registry: MagicMock) -> None:
        """Test that widget route is included."""
        controller = WidgetController(registry=mock_registry)
        routes = controller.get_routes()
        paths = [r.path for r in routes]
        assert any("/{contributor_id}/widgets/{widget_name}" in p for p in paths)

    def test_get_routes_includes_health_route(self, mock_registry: MagicMock) -> None:
        """Test that health check route is included."""
        controller = WidgetController(registry=mock_registry)
        routes = controller.get_routes()
        paths = [r.path for r in routes]
        assert any("/{contributor_id}/health/{check_name}" in p for p in paths)

    def test_get_routes_path_no_admin_prefix(self, mock_registry: MagicMock) -> None:
        """Test that route paths do not have duplicate /admin prefix.

        Routes are mounted at /admin via Mount(), so get_routes() should
        return paths like /{contributor_id}/widgets/{widget_name}, not
        /admin/{contributor_id}/widgets/{widget_name}.
        """
        controller = WidgetController(registry=mock_registry)
        routes = controller.get_routes()
        for route in routes:
            assert not route.path.startswith("/admin"), (
                f"Route path '{route.path}' should not include /admin prefix - "
                "the Mount() provides that."
            )

    def test_get_routes_has_methods(self, mock_registry: MagicMock) -> None:
        """Test that routes have correct HTTP methods."""
        controller = WidgetController(registry=mock_registry)
        routes = controller.get_routes()
        paths_to_methods = {r.path: r.methods for r in routes}
        widget_route = next(p for p in paths_to_methods if "widgets" in p)
        assert "GET" in paths_to_methods[widget_route]

    def test_get_routes_endpoint_is_callable(self, mock_registry: MagicMock) -> None:
        """Test that route endpoints are callable."""
        controller = WidgetController(registry=mock_registry)
        routes = controller.get_routes()
        for route in routes:
            assert callable(route.endpoint)

    def test_get_routes_endpoint_signature(self, mock_registry: MagicMock) -> None:
        """Test that endpoints accept request parameter."""
        controller = WidgetController(registry=mock_registry)
        routes = controller.get_routes()
        for route in routes:
            import inspect
            sig = inspect.signature(route.endpoint)
            assert "request" in sig.parameters
