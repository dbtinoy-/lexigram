"""Tests for WidgetController routing and tenant scoping."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.routing import Route

from lexigram.admin.controllers.widgets import WidgetController
from lexigram.contracts.admin.types import WidgetViewModel
from lexigram.contracts.admin.widget_content import MessageContent
from lexigram.result import Ok


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

    def test_get_routes_returns_starlette_routes(
        self, mock_registry: MagicMock
    ) -> None:
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
        """Test that route paths do not have duplicate /admin prefix."""
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


class TestWidgetControllerTenantScoping:
    """D4: dashboard widget prefs must resolve the real tenant, not hardcode 'default'."""

    @pytest.mark.asyncio
    async def test_render_widget_uses_resolved_tenant(self) -> None:
        mock_registry = MagicMock()
        mock_contributor = MagicMock()
        mock_registry.get.return_value = mock_contributor
        mock_contributor.render_widget = AsyncMock(
            return_value=Ok(WidgetViewModel(content=MessageContent(text="ok")))
        )
        settings_service = MagicMock()
        settings_service.get_widget_prefs = AsyncMock(return_value={"configs": {}})
        controller = WidgetController(registry=mock_registry)
        controller._settings_service = settings_service

        mock_request = MagicMock()
        mock_request.query_params = {}
        mock_request.state = SimpleNamespace(tenant_id="acme")

        await controller.render_widget(
            request=mock_request, contributor_id="c1", widget_name="w1"
        )

        settings_service.get_widget_prefs.assert_awaited_once_with("acme", "default")

    @pytest.mark.asyncio
    async def test_widget_config_popup_uses_resolved_tenant(self) -> None:
        controller = WidgetController(registry=MagicMock())
        controller._registry.get_all.return_value = []
        mock_request = MagicMock()
        mock_request.state = SimpleNamespace(tenant_id="acme")

        import lexigram.admin.controllers.widgets as widgets_module
        from lexigram.admin.multitenancy.adapter import resolve_tenant_id as original

        captured: dict[str, str] = {}

        async def spy(request, *, default):
            resolved = await original(request, default=default)
            captured["tenant_id"] = resolved
            return resolved

        widgets_module.resolve_tenant_id = spy
        try:
            await controller.widget_config_popup(request=mock_request, name="w1")
        finally:
            widgets_module.resolve_tenant_id = original

        assert captured["tenant_id"] == "acme"
