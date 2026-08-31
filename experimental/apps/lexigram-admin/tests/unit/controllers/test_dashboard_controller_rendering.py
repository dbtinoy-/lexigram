from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.responses import HTMLResponse

from lexigram.admin.controllers.dashboard import DashboardController
from lexigram.admin.dashboard.widgets import DashboardWidgetDefinition, WidgetRegistry
from lexigram.contracts.admin import (
    PageFilterField,
    WidgetCategory,
    WidgetKind,
    WidgetSize,
)


class TestDashboardController:
    @pytest.fixture
    def mock_renderer(self) -> MagicMock:
        renderer = MagicMock()

        def _render(content, **kwargs):
            return HTMLResponse(str(content))

        renderer.render_page.side_effect = _render
        return renderer

    @pytest.fixture
    def mock_request(self) -> MagicMock:
        request = MagicMock()
        request.query_params = {"id": "default"}
        request.app.state.admin_resources = {}
        return request

    @pytest.mark.asyncio
    async def test_index_returns_html_response(
        self,
        mock_renderer: MagicMock,
        mock_request: MagicMock,
    ) -> None:
        controller = DashboardController(renderer=mock_renderer, assembler=None)
        response = await controller.index(mock_request)
        assert isinstance(response, HTMLResponse)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_index_fallback_shows_resource_count(
        self,
        mock_renderer: MagicMock,
        mock_request: MagicMock,
    ) -> None:
        mock_request.app.state.admin_resources = {"users": ..., "posts": ...}
        controller = DashboardController(renderer=mock_renderer, assembler=None)
        response = await controller.index(mock_request)
        assert b"2" in response.body

    @pytest.mark.asyncio
    async def test_index_uses_custom_prefix_for_dashboard_actions(
        self,
        mock_renderer: MagicMock,
        mock_request: MagicMock,
    ) -> None:
        mock_request.scope = {"admin_prefix": "/backoffice"}
        mock_request.app.state.admin_resources = {"users": ...}
        controller = DashboardController(renderer=mock_renderer, assembler=None)
        response = await controller.index(mock_request)
        body = response.body
        assert b"Welcome back" in body
        assert b"/backoffice/users" in body
        assert b"/backoffice/widgets/stats" in body
        assert b"/backoffice/core/widgets/reorder" in body

    @pytest.mark.asyncio
    async def test_index_fallback_has_default_sections(
        self,
        mock_renderer: MagicMock,
        mock_request: MagicMock,
    ) -> None:
        controller = DashboardController(renderer=mock_renderer, assembler=None)
        response = await controller.index(mock_request)
        body = response.body
        assert b"space-y-6" in body
        assert b"dashboard-view" in body
        assert b"grid-cols" in body

    @pytest.mark.asyncio
    async def test_index_with_assembler_shows_contributor_widgets(
        self,
        mock_renderer: MagicMock,
        mock_request: MagicMock,
    ) -> None:
        mock_assembler = AsyncMock()
        widgets = [
            DashboardWidgetDefinition(
                name="test_widget",
                title="Test Widget Title",
                contributor="test",
                render_endpoint="/admin/test/widget",
                size=WidgetSize.MEDIUM,
                category=WidgetCategory.CUSTOM,
                order=1,
                view_kind=WidgetKind.STAT,
            ),
        ]
        mock_assembler.get_all_widgets.return_value = widgets
        controller = DashboardController(
            renderer=mock_renderer,
            assembler=mock_assembler,
        )
        response = await controller.index(mock_request)
        assert b"Test Widget Title" in response.body

    @pytest.mark.asyncio
    async def test_index_with_widget_registry_uses_htmx_cards(
        self,
        mock_renderer: MagicMock,
        mock_request: MagicMock,
    ) -> None:
        mock_assembler = AsyncMock()
        widgets = [
            DashboardWidgetDefinition(
                name="test_widget",
                title="My HTMX Widget",
                contributor="test",
                render_endpoint="/admin/test/widgets/my_widget",
                size=WidgetSize.MEDIUM,
                category=WidgetCategory.CUSTOM,
                order=1,
                view_kind=WidgetKind.STAT,
            ),
        ]
        mock_assembler.get_all_widgets.return_value = widgets

        registry = WidgetRegistry()
        controller = DashboardController(
            renderer=mock_renderer,
            assembler=mock_assembler,
            widget_registry=registry,
        )
        response = await controller.index(mock_request)
        body = response.body
        assert b"My HTMX Widget" in body
        assert b"dashboard-grid" in body
        assert b"widget-card" in body
        assert b"hx-get" in body
        assert b"hx-trigger" in body
        assert b"load" in body
        assert b"my_widget" in body

    @pytest.mark.asyncio
    async def test_index_with_widget_registry_includes_dnd_controls(
        self,
        mock_renderer: MagicMock,
        mock_request: MagicMock,
    ) -> None:
        mock_assembler = AsyncMock()
        widgets = [
            DashboardWidgetDefinition(
                name="test_widget",
                title="My HTMX Widget",
                contributor="test",
                render_endpoint="/admin/test/widgets/my_widget",
                size=WidgetSize.MEDIUM,
                category=WidgetCategory.CUSTOM,
                order=1,
                view_kind=WidgetKind.STAT,
            ),
        ]
        mock_assembler.get_all_widgets.return_value = widgets

        registry = WidgetRegistry()
        controller = DashboardController(
            renderer=mock_renderer,
            assembler=mock_assembler,
            widget_registry=registry,
        )
        response = await controller.index(mock_request)
        body = response.body
        assert b"save-layout-btn" in body
        assert b"dashboard-dnd-controls" in body
        assert b"Sortable(" in body
        assert b"initSortable" in body
        assert b"htmx:afterSwap" in body
        assert b"/admin/core/widgets/reorder" in body

    @pytest.mark.asyncio
    async def test_index_with_empty_assembler_shows_fallback(
        self,
        mock_renderer: MagicMock,
        mock_request: MagicMock,
    ) -> None:
        mock_assembler = AsyncMock()
        mock_assembler.get_all_widgets.return_value = []
        controller = DashboardController(
            renderer=mock_renderer,
            assembler=mock_assembler,
        )
        response = await controller.index(mock_request)
        body = response.body
        assert b"space-y-6" in body
        assert b"dashboard-view" in body

    @pytest.mark.asyncio
    async def test_index_handles_app_state_errors(
        self,
        mock_renderer: MagicMock,
        mock_request: MagicMock,
    ) -> None:
        mock_request.app.state.admin_resources = None
        controller = DashboardController(renderer=mock_renderer, assembler=None)
        response = await controller.index(mock_request)
        assert b"0" in response.body

    @pytest.mark.asyncio
    async def test_index_handles_missing_app_state(
        self,
        mock_renderer: MagicMock,
        mock_request: MagicMock,
    ) -> None:
        mock_request.app = MagicMock(spec_set=())
        controller = DashboardController(renderer=mock_renderer, assembler=None)
        response = await controller.index(mock_request)
        assert isinstance(response, HTMLResponse)


class FilteredDashboardController(DashboardController):
    page_filters = [
        PageFilterField(
            name="period",
            type="select",
            label="Period",
            options=(("30d", "Last 30 days"), ("90d", "Last 90 days")),
            default="30d",
        ),
    ]


class TestDashboardControllerFilters:
    @staticmethod
    def _renderer() -> MagicMock:
        renderer = MagicMock()

        def _render(content, **kwargs):
            return HTMLResponse(str(content))

        renderer.render_page.side_effect = _render
        return renderer

    @pytest.mark.asyncio
    async def test_index_renders_filter_form_and_annotates_widgets(self) -> None:
        mock_request = MagicMock()
        mock_request.query_params = {"period": "90d"}
        mock_request.session = {}
        mock_request.app.state.admin_resources = {}

        mock_assembler = AsyncMock()
        widgets = [
            DashboardWidgetDefinition(
                name="test_widget",
                title="Filt Widget",
                contributor="test",
                render_endpoint="/admin/test/widgets/my_widget",
                size=WidgetSize.MEDIUM,
                category=WidgetCategory.CUSTOM,
                order=1,
                view_kind=WidgetKind.STAT,
            ),
        ]
        mock_assembler.get_all_widgets.return_value = widgets

        controller = FilteredDashboardController(
            renderer=self._renderer(),
            assembler=mock_assembler,
            widget_registry=WidgetRegistry(),
        )
        response = await controller.index(mock_request)
        body = response.body
        assert b'name="period"' in body
        assert b'value="90d" selected' in body
        assert b"hx-get" in body
        assert b"period=90d" in body
        assert mock_request.session["admin_page_filters.dashboard"]["period"] == "90d"

    @pytest.mark.asyncio
    async def test_index_reset_clears_session_filters(self) -> None:
        mock_request = MagicMock()
        mock_request.query_params = {"reset_page_filters": "1"}
        mock_request.session = {"admin_page_filters.dashboard": {"period": "90d"}}
        mock_request.app.state.admin_resources = {}

        controller = FilteredDashboardController(
            renderer=self._renderer(),
            assembler=None,
        )
        await controller.index(mock_request)
        assert "admin_page_filters.dashboard" not in mock_request.session
