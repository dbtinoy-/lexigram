"""Tests for contributor widget rendering."""

from __future__ import annotations

import pytest

from lexigram.admin.dashboard.widgets import WidgetRegistry
from lexigram.contracts.admin import (
    DashboardWidgetDefinition,
    WidgetCategory,
    WidgetKind,
    WidgetSize,
)


class TestWidgetRegistry:
    def test_render_contributor_widgets_empty(self) -> None:
        """Empty widget list returns styled empty state."""
        registry = WidgetRegistry()
        result = registry.render_contributor_widgets([])
        assert "widget-empty-state" in result
        assert "No contributor widgets configured." in result

    def test_render_contributor_widgets_unknown_widget(self) -> None:
        """Unregistered widget type renders placeholder card."""
        registry = WidgetRegistry()
        widget = DashboardWidgetDefinition(
            name="test-widget",
            title="Test Widget",
            contributor="test",
            description="A test widget",
            category=WidgetCategory.METRICS,
            size=WidgetSize.SMALL,
            render_endpoint="/admin/test/widget",
            view_kind=WidgetKind.STAT,
        )
        result = registry.render_contributor_widgets([widget])
        assert "Test Widget" in result
        assert "widget-card" in result

    def test_render_contributor_widgets_contributor_label(self) -> None:
        """Widget card includes contributor name and description."""
        registry = WidgetRegistry()
        widget = DashboardWidgetDefinition(
            name="test-widget",
            title="Test Widget",
            description="Widget description",
            category=WidgetCategory.METRICS,
            size=WidgetSize.SMALL,
            contributor="test-contributor",
            render_endpoint="/admin/test/widget",
            view_kind=WidgetKind.STAT,
        )
        result = registry.render_contributor_widgets([widget])
        assert "test-contributor" in result
        assert "Widget description" in result

    def test_render_contributor_widgets_refresh_interval(self) -> None:
        """Widget with refresh interval includes hx-trigger for polling."""
        registry = WidgetRegistry()
        widget = DashboardWidgetDefinition(
            name="polling-widget",
            title="Polling Widget",
            contributor="test",
            category=WidgetCategory.METRICS,
            size=WidgetSize.SMALL,
            render_endpoint="/admin/test/poll",
            refresh_interval_seconds=30,
            view_kind=WidgetKind.STAT,
        )
        result = registry.render_contributor_widgets([widget])
        assert "every 30000ms" in result
        assert "hx-trigger" in result

    def test_render_contributor_widgets_multiple(self) -> None:
        """Multiple widgets are rendered consecutively."""
        registry = WidgetRegistry()
        widgets = [
            DashboardWidgetDefinition(
                name="widget-a",
                title="Widget A",
                contributor="test",
                category=WidgetCategory.METRICS,
                size=WidgetSize.SMALL,
                render_endpoint="/admin/widget/a",
                view_kind=WidgetKind.STAT,
            ),
            DashboardWidgetDefinition(
                name="widget-b",
                title="Widget B",
                contributor="test",
                category=WidgetCategory.METRICS,
                size=WidgetSize.MEDIUM,
                render_endpoint="/admin/widget/b",
                view_kind=WidgetKind.STAT,
            ),
        ]
        result = registry.render_contributor_widgets(widgets)
        assert "Widget A" in result
        assert "Widget B" in result
        assert "lg:col-span-2" in result  # MEDIUM size spans 2 columns
