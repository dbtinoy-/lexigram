"""Tests for admin dashboard widgets."""

import pytest

from lexigram.admin.dashboard.widgets import (
    DashboardConfig,
    DashboardWidgetDefinition,
    InMemoryDashboardStore,
    WidgetCategory,
    WidgetConfig,
    WidgetRegistry,
    WidgetSize,
    WidgetType,
)
from lexigram.contracts.admin import (
    DashboardWidgetDefinition,
    WidgetCategory,
    WidgetKind,
    WidgetSize,
)


class TestWidgetType:
    """Tests for WidgetType enum."""

    def test_widget_type_values(self) -> None:
        """Test WidgetType enum values."""
        assert WidgetType.METRIC.value == "metric"
        assert WidgetType.CHART.value == "chart"
        assert WidgetType.TABLE.value == "table"
        assert WidgetType.TEXT.value == "text"
        assert WidgetType.CUSTOM.value == "custom"
        assert WidgetType.STAT_CARD.value == "stat_card"
        assert WidgetType.ACTIVITY.value == "activity"
        assert WidgetType.HEALTH.value == "health"

    def test_widget_type_members(self) -> None:
        """Test WidgetType has expected members."""
        members = list(WidgetType)
        assert len(members) == 8

    def test_widget_type_from_string(self) -> None:
        """Test creating WidgetType from string."""
        assert WidgetType("metric") == WidgetType.METRIC
        assert WidgetType("stat_card") == WidgetType.STAT_CARD


class TestWidgetConfig:
    """Tests for WidgetConfig dataclass."""

    def test_widget_config_creation(self) -> None:
        """Test creating WidgetConfig."""
        config = WidgetConfig(
            id="widget-1",
            type=WidgetType.METRIC,
            title="Total Users",
        )
        assert config.id == "widget-1"
        assert config.type == WidgetType.METRIC
        assert config.title == "Total Users"
        assert config.config == {}
        assert config.position == {"x": 0, "y": 0, "w": 1, "h": 1}

    def test_widget_config_with_options(self) -> None:
        """Test WidgetConfig with options."""
        config = WidgetConfig(
            id="widget-1",
            type=WidgetType.CHART,
            title="Sales Chart",
            config={"chartType": "bar"},
            position={"x": 2, "y": 1, "w": 3, "h": 2},
        )
        assert config.config == {"chartType": "bar"}
        assert config.position == {"x": 2, "y": 1, "w": 3, "h": 2}

    def test_widget_config_to_dict(self) -> None:
        """Test WidgetConfig serialization."""
        config = WidgetConfig(
            id="widget-1",
            type=WidgetType.METRIC,
            title="Test",
        )
        data = config.to_dict()
        assert data["id"] == "widget-1"
        assert data["type"] == "metric"
        assert data["title"] == "Test"

    def test_widget_config_from_dict(self) -> None:
        """Test WidgetConfig deserialization."""
        data = {
            "id": "widget-1",
            "type": "chart",
            "title": "Test Chart",
            "config": {"key": "value"},
            "position": {"x": 1, "y": 2, "w": 3, "h": 4},
        }
        config = WidgetConfig.from_dict(data)
        assert config.id == "widget-1"
        assert config.type == WidgetType.CHART
        assert config.title == "Test Chart"
        assert config.config == {"key": "value"}
        assert config.position == {"x": 1, "y": 2, "w": 3, "h": 4}


class TestDashboardConfig:
    """Tests for DashboardConfig dataclass."""

    def test_dashboard_config_creation(self) -> None:
        """Test creating DashboardConfig."""
        dashboard = DashboardConfig(
            id="dashboard-1",
            name="My Dashboard",
        )
        assert dashboard.id == "dashboard-1"
        assert dashboard.name == "My Dashboard"
        assert dashboard.widgets == []
        assert dashboard.layout == {}

    def test_dashboard_config_with_widgets(self) -> None:
        """Test DashboardConfig with widgets."""
        widget = WidgetConfig(
            id="widget-1",
            type=WidgetType.METRIC,
            title="Test",
        )
        dashboard = DashboardConfig(
            id="dashboard-1",
            name="Test Dashboard",
            widgets=[widget],
            layout={"columns": 12},
        )
        assert len(dashboard.widgets) == 1
        assert dashboard.layout == {"columns": 12}

    def test_dashboard_config_to_dict(self) -> None:
        """Test DashboardConfig serialization."""
        dashboard = DashboardConfig(
            id="dashboard-1",
            name="Test",
        )
        data = dashboard.to_dict()
        assert data["id"] == "dashboard-1"
        assert data["name"] == "Test"
        assert "widgets" in data
        assert "created_at" in data

    def test_dashboard_config_from_dict(self) -> None:
        """Test DashboardConfig deserialization."""
        data = {
            "id": "dashboard-1",
            "name": "Imported Dashboard",
            "widgets": [],
            "layout": {},
        }
        dashboard = DashboardConfig.from_dict(data)
        assert dashboard.id == "dashboard-1"
        assert dashboard.name == "Imported Dashboard"


class TestInMemoryDashboardStore:
    """Tests for InMemoryDashboardStore."""

    @pytest.mark.asyncio
    async def test_save_and_load(self) -> None:
        """Test saving and loading dashboard."""
        store = InMemoryDashboardStore()
        dashboard = DashboardConfig(id="dash-1", name="Test")

        result = await store.save(dashboard)
        assert result is True

        loaded = await store.load("dash-1")
        assert loaded is not None
        assert loaded.id == "dash-1"

    @pytest.mark.asyncio
    async def test_list(self) -> None:
        """Test listing dashboards."""
        store = InMemoryDashboardStore()

        await store.save(DashboardConfig(id="dash-1", name="Dashboard 1"))
        await store.save(DashboardConfig(id="dash-2", name="Dashboard 2"))

        dashboards = await store.list()
        assert len(dashboards) == 2

    @pytest.mark.asyncio
    async def test_delete(self) -> None:
        """Test deleting dashboard."""
        store = InMemoryDashboardStore()
        await store.save(DashboardConfig(id="dash-1", name="Test"))

        result = await store.delete("dash-1")
        assert result is True

        loaded = await store.load("dash-1")
        assert loaded is None


class TestWidgetRegistry:
    """Tests for WidgetRegistry."""

    def test_register_and_get(self) -> None:
        """Test registering and getting widget."""
        registry = WidgetRegistry()

        class DummyWidget:
            pass

        registry.register("custom", DummyWidget)
        assert registry.get("custom") == DummyWidget

    def test_get_missing(self) -> None:
        """Test getting missing widget returns None."""
        registry = WidgetRegistry()
        assert registry.get("nonexistent") is None

    def test_list_types(self) -> None:
        """Test listing widget types."""
        registry = WidgetRegistry()

        class WidgetA:
            pass

        class WidgetB:
            pass

        registry.register("widget-a", WidgetA)
        registry.register("widget-b", WidgetB)

        types = registry.list_types()
        assert "widget-a" in types
        assert "widget-b" in types

    def test_create_widget(self) -> None:
        """Test creating widget instance."""
        registry = WidgetRegistry()

        class TestWidget:
            def __init__(self):
                self.created = True

        registry.register("test", TestWidget)
        widget = registry.create_widget("test")
        assert widget is not None
        assert widget.created is True

    def test_render_contributor_widgets_has_data_widget_name(self) -> None:
        """Test each widget card includes a data-widget-name attribute."""
        registry = WidgetRegistry()
        widgets = [
            DashboardWidgetDefinition(
                name="alpha_widget",
                title="Alpha",
                contributor="test",
                render_endpoint="/admin/test/alpha",
                size=WidgetSize.MEDIUM,
                category=WidgetCategory.CUSTOM,
                order=1,
                view_kind=WidgetKind.STAT,
            ),
            DashboardWidgetDefinition(
                name="beta_widget",
                title="Beta",
                contributor="test",
                render_endpoint="/admin/test/beta",
                size=WidgetSize.SMALL,
                category=WidgetCategory.CUSTOM,
                order=2,
                view_kind=WidgetKind.STAT,
            ),
        ]
        html = registry.render_contributor_widgets(widgets)
        assert 'data-widget-name="alpha_widget"' in html
        assert 'data-widget-name="beta_widget"' in html
        assert html.count('data-widget-name="') == 2

    def test_render_contributor_widgets_default_card(self) -> None:
        """Test render returns standard HTMX card when no IWidget registered."""
        registry = WidgetRegistry()
        widgets = [
            DashboardWidgetDefinition(
                name="test_widget",
                title="My Widget",
                contributor="test",
                render_endpoint="/admin/test/widgets/data",
                size=WidgetSize.MEDIUM,
                category=WidgetCategory.CUSTOM,
                order=1,
                view_kind=WidgetKind.STAT,
            ),
        ]
        html = registry.render_contributor_widgets(widgets)
        assert "My Widget" in html
        assert "widget-card" in html
        assert "widget-placeholder" not in html
        assert "hx-get" in html
        assert "/admin/test/widgets/data" in html

    def test_render_contributor_widgets_with_widget(self) -> None:
        """Test render returns HTMX card when IWidget is registered."""
        registry = WidgetRegistry()

        class DummyIWidget:
            async def render(self, config):
                return "<div>dummy</div>"

            def get_default_config(self):
                return {}

        registry.register("test_widget", DummyIWidget)
        widgets = [
            DashboardWidgetDefinition(
                name="test_widget",
                title="My Card",
                contributor="test",
                render_endpoint="/admin/test/widgets/data",
                size=WidgetSize.SMALL,
                category=WidgetCategory.CUSTOM,
                order=1,
                view_kind=WidgetKind.STAT,
            ),
        ]
        html = registry.render_contributor_widgets(widgets)
        assert "My Card" in html
        assert "widget-card" in html
        assert "hx-get" in html
        assert "/admin/test/widgets/data" in html

    def test_render_contributor_widgets_sizing(self) -> None:
        """Test widget size maps to col-span classes."""
        registry = WidgetRegistry()
        full_widget = DashboardWidgetDefinition(
            name="full_widget",
            title="Full Width",
            contributor="test",
            render_endpoint="/admin/test/w1",
            size=WidgetSize.FULL,
            category=WidgetCategory.CUSTOM,
            order=1,
            view_kind=WidgetKind.STAT,
        )
        small_widget = DashboardWidgetDefinition(
            name="small_widget",
            title="Small",
            contributor="test",
            render_endpoint="/admin/test/w2",
            size=WidgetSize.SMALL,
            category=WidgetCategory.CUSTOM,
            order=2,
            view_kind=WidgetKind.STAT,
        )
        html = registry.render_contributor_widgets([full_widget, small_widget])
        # FULL should get lg:col-span-4
        assert "lg:col-span-4" in html
        # SMALL should NOT get a col-span class (empty string)
        assert html.count("lg:col-span-4") == 1

    def test_render_contributor_widgets_auto_refresh(self) -> None:
        """Test refresh interval adds polling trigger."""
        registry = WidgetRegistry()

        class DummyIWidget:
            async def render(self, config):
                return "<div>dummy</div>"

            def get_default_config(self):
                return {}

        registry.register("refresh_widget", DummyIWidget)
        widgets = [
            DashboardWidgetDefinition(
                name="refresh_widget",
                title="Live Stats",
                contributor="test",
                render_endpoint="/admin/test/live",
                size=WidgetSize.MEDIUM,
                category=WidgetCategory.METRICS,
                order=1,
                view_kind=WidgetKind.STAT,
                refresh_interval_seconds=10,
            ),
        ]
        html = registry.render_contributor_widgets(widgets)
        # Should contain the every-Nms trigger with a stagger delay
        assert "every 10000ms" in html
        assert "load delay:0ms, every" in html

        # Stagger delays scale with widget index
        widgets2 = [
            *widgets,
            DashboardWidgetDefinition(
                name="second_widget",
                title="Second",
                contributor="test",
                render_endpoint="/admin/test/second",
                size=WidgetSize.SMALL,
                category=WidgetCategory.CUSTOM,
                order=2,
                view_kind=WidgetKind.STAT,
                refresh_interval_seconds=0,
            ),
        ]
        html2 = registry.render_contributor_widgets(widgets2)
        assert "load delay:0ms, every" in html2
        assert "load delay:350ms" in html2

    def test_render_contributor_widgets_no_refresh(self) -> None:
        """Test no polling trigger when interval is zero."""
        registry = WidgetRegistry()

        class DummyIWidget:
            async def render(self, config):
                return "<div>dummy</div>"

            def get_default_config(self):
                return {}

        registry.register("static_widget", DummyIWidget)
        widgets = [
            DashboardWidgetDefinition(
                name="static_widget",
                title="Static",
                contributor="test",
                render_endpoint="/admin/test/static",
                size=WidgetSize.SMALL,
                category=WidgetCategory.CUSTOM,
                order=1,
                view_kind=WidgetKind.STAT,
                refresh_interval_seconds=0,
            ),
        ]
        html = registry.render_contributor_widgets(widgets)
        assert "every" not in html
        # Should still have the load trigger with a stagger delay
        assert 'hx-trigger="load delay:0ms"' in html

    def test_render_contributor_widgets_appends_page_filters(self) -> None:
        """Test widget fetch URLs carry the page-level filter state."""
        registry = WidgetRegistry()
        widgets = [
            DashboardWidgetDefinition(
                name="alpha_widget",
                title="Alpha",
                contributor="test",
                render_endpoint="/admin/test/alpha",
                size=WidgetSize.MEDIUM,
                category=WidgetCategory.CUSTOM,
                order=1,
                view_kind=WidgetKind.STAT,
            ),
        ]
        html = registry.render_contributor_widgets(
            widgets,
            page_filters={"period": "90d", "active": True},
        )
        assert 'hx-get="/admin/test/alpha?period=90d&amp;active=True"' in html

    def test_render_contributor_widgets_plain_url_without_filters(self) -> None:
        """Test fetch URLs stay unchanged when no page filters are given."""
        registry = WidgetRegistry()
        widgets = [
            DashboardWidgetDefinition(
                name="alpha_widget",
                title="Alpha",
                contributor="test",
                render_endpoint="/admin/test/alpha",
                size=WidgetSize.MEDIUM,
                category=WidgetCategory.CUSTOM,
                order=1,
                view_kind=WidgetKind.STAT,
            ),
        ]
        html = registry.render_contributor_widgets(widgets)
        assert 'hx-get="/admin/test/alpha"' in html
