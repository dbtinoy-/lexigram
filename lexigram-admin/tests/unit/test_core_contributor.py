"""Tests for CoreAdminContributor."""

from __future__ import annotations

import pytest

from lexigram.admin.contributors.core import CoreAdminContributor
from lexigram.contracts.admin.protocols import AdminContributorProtocol
from lexigram.contracts.admin.types import WidgetCategory, WidgetParams


class TestCoreAdminContributor:
    def test_implements_protocol(self) -> None:
        contrib = CoreAdminContributor()
        assert isinstance(contrib, AdminContributorProtocol)

    def test_properties(self) -> None:
        contrib = CoreAdminContributor()
        assert contrib.name == "core"
        assert contrib.display_name == "Core"
        assert contrib.group == "system"
        assert contrib.priority == 0

    def test_dashboard_widgets_present(self) -> None:
        contrib = CoreAdminContributor()
        widgets = contrib.get_dashboard_widgets()
        assert len(widgets) >= 1
        names = [w.name for w in widgets]
        assert "health" in names

    def test_health_widget_category(self) -> None:
        contrib = CoreAdminContributor()
        widgets = contrib.get_dashboard_widgets()
        health_widget = next(w for w in widgets if w.name == "health")
        assert health_widget.category == WidgetCategory.HEALTH

    def test_chart_metrics_widget_definition(self) -> None:
        contrib = CoreAdminContributor()
        widgets = contrib.get_dashboard_widgets()
        chart_widget = next(w for w in widgets if w.name == "chart_metrics")
        assert chart_widget.title == "Framework Metrics"
        assert chart_widget.category == WidgetCategory.METRICS
        assert chart_widget.size.value == "full"
        assert chart_widget.refresh_interval_seconds == 30

    @pytest.mark.asyncio
    async def test_chart_metrics_widget_renders_html(self) -> None:
        contrib = CoreAdminContributor()
        params = WidgetParams()
        result = await contrib.render_widget("chart_metrics", params)
        assert result.is_ok()
        body = result.unwrap().body
        assert isinstance(body, str)
        assert len(body) > 0
        assert "Framework Metrics" in body

    @pytest.mark.asyncio
    async def test_all_widgets_render(self) -> None:
        contrib = CoreAdminContributor()
        widgets = contrib.get_dashboard_widgets()
        params = WidgetParams()
        for w in widgets:
            result = await contrib.render_widget(w.name, params)
            assert result.is_ok(), f"Widget '{w.name}' failed to render"
            assert len(result.unwrap().body) > 0

    def test_navigation_items_present(self) -> None:
        contrib = CoreAdminContributor()
        nav = contrib.get_navigation_items()
        assert len(nav) >= 1
        labels = [n.label for n in nav]
        assert "Dashboard" in labels
