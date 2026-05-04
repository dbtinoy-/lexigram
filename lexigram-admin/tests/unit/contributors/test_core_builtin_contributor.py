"""Tests for the built-in core contributor's structured widget content."""

from __future__ import annotations

from lexigram.admin.contributors.core import CoreAdminContributor
from lexigram.contracts.admin.types import WidgetParams
from lexigram.contracts.admin.widget_content import (
    ChartContent,
    EmptyContent,
    WidgetKind,
)


async def test_health_widget_returns_empty_content_placeholder() -> None:
    contributor = CoreAdminContributor()
    result = await contributor.render_widget("health", WidgetParams())
    vm = result.unwrap()
    assert isinstance(vm.content, EmptyContent)


async def test_activity_widget_returns_empty_content_placeholder() -> None:
    contributor = CoreAdminContributor()
    result = await contributor.render_widget("activity", WidgetParams())
    vm = result.unwrap()
    assert isinstance(vm.content, EmptyContent)


async def test_chart_metrics_widget_returns_chart_content() -> None:
    contributor = CoreAdminContributor()
    result = await contributor.render_widget("chart_metrics", WidgetParams())
    vm = result.unwrap()
    assert isinstance(vm.content, ChartContent)
    assert len(vm.content.points) == 5


def test_widget_definitions_declare_widget_kind() -> None:
    contributor = CoreAdminContributor()
    defs = {widget.name: widget for widget in contributor.get_dashboard_widgets()}
    assert defs["health"].view_kind == WidgetKind.EMPTY
    assert defs["activity"].view_kind == WidgetKind.EMPTY
    assert defs["chart_metrics"].view_kind == WidgetKind.CHART
