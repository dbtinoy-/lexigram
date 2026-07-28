"""Tests for web admin widget rendering.

Tests the WebAdminContributor widget handler dispatch, renderer,
and template integration.
"""

from __future__ import annotations

import pytest

from lexigram.contracts.admin.errors import WidgetNotFoundError
from lexigram.contracts.admin.types import WidgetParams, WidgetViewModel
from lexigram.web.admin.contributor import WebAdminContributor
from lexigram.web.admin.widgets import (
    ActiveConnectionsViewModel,
    ActiveConnectionsWidgetHandler,
    PackageWidgetRenderer,
    RequestRateViewModel,
    RequestRateWidgetHandler,
    ServerStatusViewModel,
    ServerStatusWidgetHandler,
)


class TestWebAdminContributor:
    """Test WebAdminContributor widget rendering."""

    @pytest.fixture
    async def contributor(self) -> WebAdminContributor:
        """Create a contributor instance with mock dependencies."""
        from unittest.mock import AsyncMock, MagicMock

        from lexigram.result import Ok

        mock_server_status = MagicMock(spec=ServerStatusWidgetHandler)
        mock_server_status.get_data = AsyncMock(return_value=Ok(MagicMock()))

        mock_connections = MagicMock(spec=ActiveConnectionsWidgetHandler)
        mock_connections.get_data = AsyncMock(return_value=Ok(MagicMock()))

        mock_request_rate = MagicMock(spec=RequestRateWidgetHandler)
        mock_request_rate.get_data = AsyncMock(return_value=Ok(MagicMock()))

        mock_renderer = MagicMock(spec=PackageWidgetRenderer)
        mock_renderer.render = MagicMock(return_value="<div>Rendered Widget</div>")

        contributor = WebAdminContributor()
        mock_container = MagicMock()
        mock_container.resolve = AsyncMock(
            side_effect=lambda cls: {
                ServerStatusWidgetHandler: mock_server_status,
                ActiveConnectionsWidgetHandler: mock_connections,
                RequestRateWidgetHandler: mock_request_rate,
                PackageWidgetRenderer: mock_renderer,
            }.get(cls)
        )
        await contributor.on_admin_boot(mock_container)
        return contributor

    @pytest.fixture
    def widget_params(self) -> WidgetParams:
        """Create widget parameters."""
        return WidgetParams()

    @pytest.mark.asyncio
    async def test_render_server_status_widget(
        self,
        contributor: WebAdminContributor,
        widget_params: WidgetParams,
    ) -> None:
        """Test rendering the server_status widget."""
        result = await contributor.render_widget("server_status", widget_params)

        assert result.is_ok()
        vm = result.unwrap()
        assert isinstance(vm, WidgetViewModel)
        assert "Rendered Widget" in vm.body

    @pytest.mark.asyncio
    async def test_render_active_connections_widget(
        self,
        contributor: WebAdminContributor,
        widget_params: WidgetParams,
    ) -> None:
        """Test rendering the active_connections widget."""
        result = await contributor.render_widget("active_connections", widget_params)

        assert result.is_ok()
        vm = result.unwrap()
        assert isinstance(vm, WidgetViewModel)
        assert "Rendered Widget" in vm.body

    @pytest.mark.asyncio
    async def test_render_request_rate_widget(
        self,
        contributor: WebAdminContributor,
        widget_params: WidgetParams,
    ) -> None:
        """Test rendering the request_rate widget."""
        result = await contributor.render_widget("request_rate", widget_params)

        assert result.is_ok()
        vm = result.unwrap()
        assert isinstance(vm, WidgetViewModel)
        assert "Rendered Widget" in vm.body

    @pytest.mark.asyncio
    async def test_render_unknown_widget_returns_error(
        self,
        contributor: WebAdminContributor,
        widget_params: WidgetParams,
    ) -> None:
        """Test that rendering an unknown widget returns WidgetNotFoundError."""
        result = await contributor.render_widget("unknown_widget", widget_params)

        assert result.is_err()
        error = result.unwrap_err()
        assert isinstance(error, WidgetNotFoundError)
        assert "unknown_widget" in str(error)
        assert "web" in str(error)

    def test_contributor_metadata(self, contributor: WebAdminContributor) -> None:
        """Test contributor metadata."""
        assert contributor.name == "web"
        assert contributor.display_name == "Web Server"
        assert contributor.group == "infrastructure"
        assert contributor.priority == 10

    def test_dashboard_widgets_defined(self, contributor: WebAdminContributor) -> None:
        """Test that dashboard widgets are defined."""
        widgets = contributor.get_dashboard_widgets()

        assert len(widgets) == 3
        widget_names = [w.name for w in widgets]
        assert "server_status" in widget_names
        assert "active_connections" in widget_names
        assert "request_rate" in widget_names

    def test_navigation_items_defined(self, contributor: WebAdminContributor) -> None:
        """Test that navigation items are defined."""
        nav_items = contributor.get_navigation_items()

        assert len(nav_items) > 0
        assert nav_items[0].label == "Web"

    def test_health_definitions_defined(self, contributor: WebAdminContributor) -> None:
        """Test that health definitions are defined."""
        health_defs = contributor.get_health_definitions()

        assert len(health_defs) > 0
        health_names = [h.name for h in health_defs]
        assert "web.server" in health_names

    def test_actions_defined(self, contributor: WebAdminContributor) -> None:
        """Test that admin actions are defined."""
        actions = contributor.get_actions()

        assert len(actions) > 0
        action_names = [a.name for a in actions]
        assert "reload_routes" in action_names


class TestWidgetHandlers:
    """Test individual widget handlers."""

    @pytest.mark.asyncio
    async def test_server_status_handler(self) -> None:
        """Test server_status handler returns viewmodel."""
        handler = ServerStatusWidgetHandler()
        result = await handler.get_data(WidgetParams())

        assert result.is_ok()
        viewmodel = result.unwrap()
        assert isinstance(viewmodel, ServerStatusViewModel)
        assert viewmodel.is_running is True
        assert viewmodel.uptime_seconds > 0
        assert viewmodel.server_version

    @pytest.mark.asyncio
    async def test_active_connections_handler(self) -> None:
        """Test active_connections handler returns viewmodel."""
        handler = ActiveConnectionsWidgetHandler()
        result = await handler.get_data(WidgetParams())

        assert result.is_ok()
        viewmodel = result.unwrap()
        assert isinstance(viewmodel, ActiveConnectionsViewModel)
        assert viewmodel.active >= 0
        assert viewmodel.peak >= viewmodel.active
        assert viewmodel.max_allowed > viewmodel.peak

    @pytest.mark.asyncio
    async def test_request_rate_handler(self) -> None:
        """Test request_rate handler returns viewmodel."""
        handler = RequestRateWidgetHandler()
        result = await handler.get_data(WidgetParams())

        assert result.is_ok()
        viewmodel = result.unwrap()
        assert isinstance(viewmodel, RequestRateViewModel)
        assert viewmodel.requests_per_second >= 0
        assert viewmodel.total_requests >= 0
        assert 0 <= viewmodel.error_rate_pct <= 100


class TestPackageWidgetRenderer:
    """Test Jinja2 widget renderer."""

    @pytest.fixture
    def renderer(self) -> PackageWidgetRenderer:
        """Create a renderer instance."""
        return PackageWidgetRenderer()

    def test_render_server_status_template(
        self, renderer: PackageWidgetRenderer
    ) -> None:
        """Test rendering server_status template."""
        context = {
            "title": "Server Status",
            "is_running": True,
            "uptime_seconds": 3600,
            "server_version": "1.0.0",
        }
        html = renderer.render("server_status.html", context)

        assert "Server Status" in html
        assert "Running" in html
        assert "1.0" in html  # From 3600/3600 = 1 hour

    def test_render_active_connections_template(
        self,
        renderer: PackageWidgetRenderer,
    ) -> None:
        """Test rendering active_connections template."""
        context = {
            "title": "Active Connections",
            "active": 42,
            "peak": 128,
            "max_allowed": 512,
        }
        html = renderer.render("active_connections.html", context)

        assert "Active Connections" in html
        assert "42" in html
        assert "128" in html
        assert "512" in html

    def test_render_request_rate_template(
        self,
        renderer: PackageWidgetRenderer,
    ) -> None:
        """Test rendering request_rate template."""
        context = {
            "title": "Request Rate",
            "requests_per_second": 12.5,
            "total_requests": 45000,
            "error_rate_pct": 0.5,
        }
        html = renderer.render("request_rate.html", context)

        assert "Request Rate" in html
        assert "12.5" in html
        assert "45000" in html
        assert "0.5" in html

    def test_render_template_not_found(self, renderer: PackageWidgetRenderer) -> None:
        """Test that rendering non-existent template raises error."""
        with pytest.raises(Exception):  # jinja2.TemplateNotFound
            renderer.render("nonexistent.html", {})


__all__ = [
    "TestWebAdminContributor",
    "TestWidgetHandlers",
    "TestPackageWidgetRenderer",
]
