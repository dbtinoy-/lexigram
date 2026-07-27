"""Tests for the built-in core contributor's structured widget content."""

from __future__ import annotations

from lexigram.admin.contributors.core import CoreAdminContributor
from lexigram.contracts.admin import StatContent, Tone, WidgetParams
from lexigram.contracts.admin.widget_content import (
    ChartContent,
    EmptyContent,
    WidgetKind,
)
from lexigram.contracts.core import HealthStatus


class _FakeGauge:
    def get_value(self) -> float:
        return 12.0


class _FakeHealthRegistry:
    async def run_all(self) -> tuple[object, dict[str, object]]:
        return (
            HealthStatus.HEALTHY,
            {
                "liveness": {
                    "status": "healthy",
                    "checks": [{"status": "healthy", "component": "sql"}],
                },
                "readiness": {"status": "healthy", "checks": []},
            },
        )

    async def run_check(self, name: str) -> dict[str, object]:
        if name == "sql":
            return {"status": "healthy", "component": "sql"}
        return {"status": "UNKNOWN", "component": name}


class _FakeMetrics:
    def get_metric(self, name: str) -> object | None:
        return _FakeGauge() if name == "requests_total" else None

    def get_all_metrics(self) -> dict[str, object]:
        return {"requests_total": _FakeGauge()}


async def test_health_widget_returns_empty_content_placeholder() -> None:
    contributor = CoreAdminContributor()
    result = await contributor.render_widget("health", WidgetParams())
    vm = result.unwrap()
    assert isinstance(vm.content, EmptyContent)


async def test_health_widget_reports_aggregate_status() -> None:
    contributor = CoreAdminContributor(
        health=_FakeHealthRegistry(),
        metrics=_FakeMetrics(),
    )
    result = await contributor.render_widget("health", WidgetParams())
    vm = result.unwrap()
    assert isinstance(vm.content, StatContent)
    assert "healthy" in str(vm.content)


async def test_activity_widget_returns_empty_content_placeholder() -> None:
    contributor = CoreAdminContributor()
    result = await contributor.render_widget("activity", WidgetParams())
    vm = result.unwrap()
    assert isinstance(vm.content, EmptyContent)


async def test_chart_metrics_widget_degrades_without_source() -> None:
    contributor = CoreAdminContributor()
    result = await contributor.render_widget("chart_metrics", WidgetParams())
    vm = result.unwrap()
    assert isinstance(vm.content, ChartContent)
    assert len(vm.content.points) == 1
    assert vm.content.points[0].label == "Not measured"
    assert vm.content.points[0].tone is Tone.WARNING


async def test_chart_metrics_reads_metrics_capability() -> None:
    contributor = CoreAdminContributor(metrics=_FakeMetrics())
    result = await contributor.render_widget("chart_metrics", WidgetParams())
    vm = result.unwrap()
    assert isinstance(vm.content, ChartContent)
    assert [p.label for p in vm.content.points] == ["requests_total"]
    assert vm.content.points[0].value == 12.0


async def test_render_health_check_uses_registry() -> None:
    contributor = CoreAdminContributor(health=_FakeHealthRegistry())
    result = await contributor.render_health_check("sql")
    payload = result.unwrap()
    assert payload.component == "sql"
    assert payload.status is HealthStatus.HEALTHY


async def test_render_health_check_admin_core_uses_run_all() -> None:
    contributor = CoreAdminContributor(health=_FakeHealthRegistry())
    result = await contributor.render_health_check("admin_core")
    payload = result.unwrap()
    assert payload.component == "Admin Core"
    assert payload.status is HealthStatus.HEALTHY


async def test_render_health_check_degrades_without_registry() -> None:
    contributor = CoreAdminContributor()
    result = await contributor.render_health_check("admin_core")
    payload = result.unwrap()
    assert payload.status is HealthStatus.UNKNOWN


def test_widget_definitions_declare_widget_kind() -> None:
    contributor = CoreAdminContributor()
    defs = {widget.name: widget for widget in contributor.get_dashboard_widgets()}
    assert defs["health"].view_kind == WidgetKind.EMPTY
    assert defs["activity"].view_kind == WidgetKind.EMPTY
    assert defs["chart_metrics"].view_kind == WidgetKind.CHART


__all__ = [
    "test_activity_widget_returns_empty_content_placeholder",
    "test_chart_metrics_reads_metrics_capability",
    "test_chart_metrics_widget_degrades_without_source",
    "test_health_widget_reports_aggregate_status",
    "test_health_widget_returns_empty_content_placeholder",
    "test_render_health_check_admin_core_uses_run_all",
    "test_render_health_check_degrades_without_registry",
    "test_render_health_check_uses_registry",
    "test_widget_definitions_declare_widget_kind",
]
