"""Tests for the built-in core contributor's structured widget content."""

from __future__ import annotations

from lexigram.admin.contributors.core import CoreAdminContributor
from lexigram.admin.dashboard.resource_inventory import ResourceInventory
from lexigram.contracts.admin import StatContent, Tone, WidgetParams
from lexigram.contracts.admin.widget_content import (
    ChartContent,
    EmptyContent,
    WidgetKind,
)
from lexigram.contracts.admin.types import WidgetCategory
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
    assert defs["activity"].view_kind == WidgetKind.TABLE
    assert defs["chart_metrics"].view_kind == WidgetKind.CHART
    assert defs["resources"].view_kind == WidgetKind.STAT


def test_resource_overview_definition_uses_resources_category() -> None:
    contributor = CoreAdminContributor()
    defs = {widget.name: widget for widget in contributor.get_dashboard_widgets()}
    widget = defs["resources"]
    assert widget.category == WidgetCategory.RESOURCES
    assert widget.render_endpoint.endswith("/core/widgets/resources")
    assert widget.title == "Resource Overview"


async def test_resource_overview_without_inventory_returns_empty_content() -> None:
    contributor = CoreAdminContributor()
    result = await contributor.render_widget("resources", WidgetParams())
    vm = result.unwrap()
    assert isinstance(vm.content, EmptyContent)


async def test_resource_overview_with_empty_inventory_returns_empty_content() -> None:
    contributor = CoreAdminContributor()
    contributor.set_resource_inventory(ResourceInventory({}))
    result = await contributor.render_widget("resources", WidgetParams())
    assert isinstance(result.unwrap().content, EmptyContent)


async def test_resource_overview_renders_formatted_stat_cards() -> None:
    class _Source:
        def __init__(self, total: int) -> None:
            self._total = total

        async def count(self, query: object) -> int:
            return self._total

    class _Broken:
        async def count(self, query: object) -> int:
            raise RuntimeError("db down")

    class _Resource:
        def __init__(self, source: object, label: str, icon: str) -> None:
            self._data_source = source
            self.label = label
            self.icon = icon

    contributor = CoreAdminContributor()
    contributor.set_resource_inventory(
        ResourceInventory(
            {
                "products": _Resource(_Source(1234), "Products", "package"),
                "orders": _Resource(_Broken(), "Orders", "shopping-cart"),
            }
        )
    )
    result = await contributor.render_widget("resources", WidgetParams())
    content = result.unwrap().content
    assert isinstance(content, StatContent)
    by_label = {stat.label: stat for stat in content.stats}
    assert by_label["Products"].value == "1,234"
    assert by_label["Products"].icon == "package"
    assert by_label["Orders"].value == "—"


def test_navigation_omits_exports_until_enabled() -> None:
    contributor = CoreAdminContributor()
    labels = [item.label for item in contributor.get_navigation_items()]
    assert labels == ["Dashboard"]


def test_navigation_includes_exports_after_enable() -> None:
    contributor = CoreAdminContributor()
    contributor.enable_export_center("/admin/exports")
    items = {item.label: item for item in contributor.get_navigation_items()}
    assert "Exports" in items
    exports = items["Exports"]
    assert exports.url == "/admin/exports"
    assert exports.icon == "download"
    assert exports.group == ""
    assert items["Dashboard"].order < exports.order


__all__ = [
    "test_chart_metrics_reads_metrics_capability",
    "test_chart_metrics_widget_degrades_without_source",
    "test_health_widget_reports_aggregate_status",
    "test_health_widget_returns_empty_content_placeholder",
    "test_navigation_includes_exports_after_enable",
    "test_navigation_omits_exports_until_enabled",
    "test_render_health_check_admin_core_uses_run_all",
    "test_render_health_check_degrades_without_registry",
    "test_render_health_check_uses_registry",
    "test_resource_overview_definition_uses_resources_category",
    "test_resource_overview_renders_formatted_stat_cards",
    "test_resource_overview_with_empty_inventory_returns_empty_content",
    "test_resource_overview_without_inventory_returns_empty_content",
    "test_widget_definitions_declare_widget_kind",
]
