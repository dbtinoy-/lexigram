"""Tests for DashboardController."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.responses import HTMLResponse

from lexigram.admin.controllers.dashboard import DashboardController
from lexigram.admin.dashboard.widgets import WidgetRegistry, DashboardWidgetDefinition
from lexigram.contracts.admin.types import WidgetCategory, WidgetSize


class TestDashboardController:
    """Tests for DashboardController.index()."""

    @pytest.fixture
    def mock_renderer(self) -> MagicMock:
        """Return a mock AdminRenderer whose render_page returns HTMLResponse."""
        renderer = MagicMock()

        def _render(content, **kwargs):
            return HTMLResponse(str(content))

        renderer.render_page.side_effect = _render
        return renderer

    @pytest.fixture
    def mock_request(self) -> MagicMock:
        """Return a mock Request with query params and app state."""
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
        """Verify index() returns an HTMLResponse with status 200.

        The controller renders the dashboard and wraps it in the admin
        shell via ``render_admin()``.
        """
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
        """Verify fallback renders the correct resource count in response body.

        When ``admin_resources`` contains two entries, the Resources stat
        should display "2".
        """
        mock_request.app.state.admin_resources = {"users": ..., "posts": ...}
        controller = DashboardController(renderer=mock_renderer, assembler=None)
        response = await controller.index(mock_request)
        assert b"2" in response.body

    @pytest.mark.asyncio
    async def test_index_fallback_has_default_sections(
        self,
        mock_renderer: MagicMock,
        mock_request: MagicMock,
    ) -> None:
        """Verify fallback response contains expected UI class names.

        The fallback dashboard should include ``space-y-6``,
        ``dashboard-view``, and grid layout classes.
        """
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
        """Verify assembler widgets are rendered when an assembler is provided.

        When ``self.assembler`` is set and ``get_all_widgets()`` returns
        widgets, each widget's title should appear in the response.
        """
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
        """Verify assembler + widget_registry renders HTMX lazy-load cards.

        When both ``assembler`` and ``widget_registry`` are provided, the
        controller uses ``WidgetRegistry.render_contributor_widgets()``
        to render the widget grid. Each widget card should use HTMX
        lazy-loading from the contributor's ``render_endpoint``.
        """
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
        # Should contain the widget title
        assert b"My HTMX Widget" in body
        # Should contain the dashboard-grid zone ID
        assert b"dashboard-grid" in body
        # Should be a widget card with HTMX lazy-load attributes
        assert b"widget-card" in body
        assert b"hx-get" in body
        assert b"hx-trigger" in body
        assert b"load" in body  # hx-trigger="load"
        # Should reference the render endpoint
        assert b"my_widget" in body

    @pytest.mark.asyncio
    async def test_index_with_widget_registry_includes_dnd_controls(
        self,
        mock_renderer: MagicMock,
        mock_request: MagicMock,
    ) -> None:
        """Verify dashboard with widget_registry includes Save Layout btn + SortableJS init.

        When both ``assembler`` and ``widget_registry`` are provided, the
        rendered page should contain the drag-and-drop controls: the
        save-layout button and the inline SortableJS initialization script.
        """
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
        """Verify fallback renders when assembler returns an empty widget list.

        An assembler with no widgets should produce the same default
        overview sections as when no assembler is provided.
        """
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
        """Verify fallback handles AttributeError from app.state gracefully.

        When ``app.state`` does not have ``admin_resources``, the
        ``_get_resource_list`` helper catches the exception and returns
        an empty list, resulting in a "0" resource count.
        """
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
        """Verify fallback handles a missing app.state attribute gracefully.

        When ``request.app`` has no ``state`` attribute at all, the
        controller should still render without crashing.
        """
        mock_request.app = MagicMock(spec_set=())
        controller = DashboardController(renderer=mock_renderer, assembler=None)
        response = await controller.index(mock_request)
        assert isinstance(response, HTMLResponse)


class TestGetResourceList:
    """Tests for DashboardController._get_resource_list()."""

    @pytest.fixture
    def controller(self) -> DashboardController:
        """Return a DashboardController with no assembler."""
        return DashboardController(renderer=MagicMock(), assembler=None)

    @pytest.fixture
    def mock_request(self) -> MagicMock:
        """Return a mock Request with sorted resource names."""
        request = MagicMock()
        request.app.state.admin_resources = {
            "z_resource": ...,
            "a_resource": ...,
        }
        return request

    def test_returns_sorted_names(
        self,
        controller: DashboardController,
        mock_request: MagicMock,
    ) -> None:
        """Verify resource names are returned in alphabetical order."""
        names = controller._get_resource_list(mock_request)
        assert names == ["a_resource", "z_resource"]

    def test_returns_empty_when_no_state(
        self,
        controller: DashboardController,
        mock_request: MagicMock,
    ) -> None:
        """Verify empty list returned when app.state raises AttributeError."""
        mock_request.app = MagicMock(spec_set=())
        result = controller._get_resource_list(mock_request)
        assert result == []

    def test_returns_empty_when_no_admin_resources(
        self,
        controller: DashboardController,
        mock_request: MagicMock,
    ) -> None:
        """Verify empty list returned when admin_resources dict is empty."""
        mock_request.app.state.admin_resources = {}
        result = controller._get_resource_list(mock_request)
        assert result == []


class TestTimeSeriesHelpers:
    """Tests for DashboardController time-series helper methods."""

    @pytest.fixture
    def controller(self) -> DashboardController:
        """Return a DashboardController with no assembler."""
        return DashboardController(renderer=MagicMock(), assembler=None)

    def test_format_time_series_basic(
        self,
        controller: DashboardController,
    ) -> None:
        """Verify basic formatting of timestamp-value tuples.

        A single data point should produce a single formatted entry
        with timestamp, value, and human-readable label.
        """
        data = [(datetime(2024, 1, 15, 10, 30), 42.0)]
        result = controller.format_time_series(data, interval="hour")
        assert len(result) == 1
        entry = result[0]
        assert "timestamp" in entry
        assert entry["value"] == 42.0
        assert entry["label"] == "10:30"

    def test_format_time_series_different_intervals(
        self,
        controller: DashboardController,
    ) -> None:
        """Verify label formatting for hour, day, week, and month intervals."""
        ts = datetime(2024, 6, 15, 14, 30)
        data = [(ts, 10.0)]

        hour_result = controller.format_time_series(data, interval="hour")
        day_result = controller.format_time_series(data, interval="day")
        week_result = controller.format_time_series(data, interval="week")
        month_result = controller.format_time_series(data, interval="month")

        assert hour_result[0]["label"] == "14:30"
        assert day_result[0]["label"] == "2024-06-15"
        assert week_result[0]["label"] == "Week 24, 2024"
        assert month_result[0]["label"] == "Jun 2024"

    def test_aggregate_time_series_buckets(
        self,
        controller: DashboardController,
    ) -> None:
        """Verify data points are correctly bucketed and averaged.

        Three points in the same hour should produce one bucket with
        the average value.
        """
        ts = datetime(2024, 1, 15, 10, 15)
        data = [
            (ts, 10.0),
            (ts.replace(minute=30), 20.0),
            (ts.replace(minute=45), 30.0),
        ]
        result = controller.aggregate_time_series(data, interval="hour")
        assert len(result) == 1
        _, avg = result[0]
        assert avg == 20.0

    def test_get_bucket_key_roundtrip(
        self,
        controller: DashboardController,
    ) -> None:
        """Verify _get_bucket_key + _parse_bucket_key roundtrip.

        For each interval, the bucket key should be parseable back to
        a datetime with the same year and month.
        """
        ts = datetime(2024, 3, 15, 8, 30)
        for interval in ("hour", "day", "week", "month"):
            key = controller._get_bucket_key(ts, interval)
            parsed = controller._parse_bucket_key(key, interval)
            assert parsed.year == ts.year
            assert parsed.month == ts.month


class TestRequestCache:
    """Tests for DashboardController request-caching helpers."""

    @pytest.fixture
    def controller(self) -> DashboardController:
        """Return a DashboardController with no assembler."""
        return DashboardController(renderer=MagicMock(), assembler=None)

    def test_get_request_cache_returns_dict(
        self,
        controller: DashboardController,
    ) -> None:
        """Verify get_request_cache returns a dict."""
        mock_request = MagicMock()
        cache = controller.get_request_cache(mock_request)
        assert isinstance(cache, dict)

    @pytest.mark.asyncio
    async def test_aggregate_metric_uses_cache(
        self,
        controller: DashboardController,
    ) -> None:
        """Verify compute func is called once on repeated call with cache.

        When ``use_request_cache`` is True and the same metric is
        requested twice, the ``compute_func`` should be executed only
        once and the cached value returned on the second call.
        """
        mock_request = MagicMock()
        shared_cache: dict[str, object] = {}
        controller.get_request_cache = MagicMock(  # type: ignore[method-assign]
            return_value=shared_cache,
        )

        compute = AsyncMock(return_value=42)

        result1 = await controller.aggregate_metric(
            mock_request,
            "test_metric",
            compute,
            use_request_cache=True,
        )
        result2 = await controller.aggregate_metric(
            mock_request,
            "test_metric",
            compute,
            use_request_cache=True,
        )

        assert result1 == 42
        assert result2 == 42
        compute.assert_called_once()
