"""Core admin contributor — built-in dashboard surfaces."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, cast

from lexigram.admin.dashboard.chart_widget import ChartWidget
from lexigram.contracts.admin.contributor import BaseAdminContributor
from lexigram.contracts.admin.errors import AdminError, WidgetNotFoundError
from lexigram.contracts.admin.health_payload import HealthCheckPayload
from lexigram.contracts.admin.types import (
    AdminHealthDefinition,
    DashboardWidgetDefinition,
    NavigationContribution,
    WidgetCategory,
    WidgetParams,
    WidgetSize,
    WidgetViewModel,
)
from lexigram.contracts.core.health import HealthStatus
from lexigram.contracts.core.result import Result
from lexigram.result import Err, Ok
from lexigram.ui import ChartConfig, ChartDataPoint, ChartType

if TYPE_CHECKING:
    from lexigram.contracts.core.di import ContainerResolverProtocol


class CoreAdminContributor(BaseAdminContributor):
    """Built-in contributor providing core dashboard surfaces.

    Provides the framework health overview widget, the main dashboard
    navigation entry, and the system-wide health check surface.
    """

    name = "core"
    display_name = "Core"
    group = "system"
    icon = "layout-dashboard"
    priority = 0

    def __init__(self) -> None:
        self._container: ContainerResolverProtocol | None = None

    async def on_admin_boot(self, container: object) -> None:
        self._container = container  # type: ignore[assignment]

    def get_dashboard_widgets(self) -> Sequence[DashboardWidgetDefinition]:
        """Return core dashboard widgets: health overview, recent activity, and metrics."""
        return [
            DashboardWidgetDefinition(
                name="health",
                title="Framework Health",
                contributor="core",
                render_endpoint="/admin/core/widgets/health",
                size=WidgetSize.FULL,
                category=WidgetCategory.HEALTH,
                refresh_interval_seconds=10,
                order=0,
                icon="heart-pulse",
                description="Aggregated health status of all framework providers.",
            ),
            DashboardWidgetDefinition(
                name="activity",
                title="Recent Activity",
                contributor="core",
                render_endpoint="/admin/core/widgets/activity",
                size=WidgetSize.LARGE,
                category=WidgetCategory.ACTIVITY,
                refresh_interval_seconds=15,
                order=90,
                icon="activity",
                description="Recent admin operations and system events.",
            ),
            DashboardWidgetDefinition(
                name="chart_metrics",
                title="Framework Metrics",
                contributor="core",
                render_endpoint="/admin/core/widgets/chart_metrics",
                size=WidgetSize.FULL,
                category=WidgetCategory.METRICS,
                refresh_interval_seconds=30,
                order=50,
                icon="bar-chart-3",
                description="Key framework performance metrics visualized.",
            ),
        ]

    def get_navigation_items(self) -> Sequence[NavigationContribution]:
        """Return core navigation: Dashboard link."""
        return [
            NavigationContribution(
                label="Dashboard",
                url="/admin/",
                icon="layout-dashboard",
                group="",
                order=0,
            ),
        ]

    def get_health_definitions(self) -> Sequence[AdminHealthDefinition]:
        """Return core health definitions."""
        return [
            AdminHealthDefinition(
                name="admin_core",
                contributor="core",
                component="Admin Core",
                check_endpoint="/admin/core/health/admin_core",
                icon="shield-check",
                description="Admin panel core services health.",
            ),
        ]

    async def render_widget(
        self,
        widget_name: str,
        params: WidgetParams,
        resolver: ContainerResolverProtocol | None = None,
    ) -> Result[WidgetViewModel, AdminError]:
        """Render core widgets.

        Args:
            widget_name: Name of the widget to render.
            params: Widget parameters.

        Returns:
            Result containing a WidgetViewModel with rendered HTML in ``body``,
            or WidgetNotFoundError if the widget is not found.
        """

        if widget_name == "health":
            return cast(
                "Result[WidgetViewModel, AdminError]",
                Ok(WidgetViewModel(body=self._render_health_widget())),
            )
        if widget_name == "activity":
            return cast(
                "Result[WidgetViewModel, AdminError]",
                Ok(WidgetViewModel(body=self._render_activity_widget())),
            )
        if widget_name == "chart_metrics":
            return cast(
                "Result[WidgetViewModel, AdminError]",
                Ok(WidgetViewModel(body=self._render_chart_metrics_widget())),
            )
        result: Result[WidgetViewModel, AdminError] = cast(
            "Result[WidgetViewModel, AdminError]",
            Err(WidgetNotFoundError(self.name, widget_name)),
        )
        return result

    def _render_health_widget(self) -> str:
        """Render the framework health widget."""
        return '<div class="widget framework-health"><div class="status healthy"><span class="indicator"></span>Healthy</div></div>'

    def _render_activity_widget(self) -> str:
        """Render the recent activity widget."""
        return '<div class="widget recent-activity"><ul class="activity-list"><li class="activity-item">No recent activity</li></ul></div>'

    def _render_chart_metrics_widget(self) -> str:
        """Render the framework metrics bar chart widget."""
        data = [
            ChartDataPoint(label="Active Users", value=847, color="blue"),
            ChartDataPoint(label="Requests/min", value=2341, color="green"),
            ChartDataPoint(label="Error Rate", value=1.2, color="red"),
            ChartDataPoint(label="Avg Latency", value=45, color="amber"),
            ChartDataPoint(label="Memory %", value=68, color="purple"),
        ]
        chart = ChartWidget(
            title="Framework Metrics",
            chart_type=ChartType.BAR,
            data=data,
            chart_config=ChartConfig(
                show_grid=True,
                show_labels=True,
                animate=True,
                height="200px",
            ),
            refresh_interval=30,
            col_span=1,
        )
        return str(chart)

    async def render_health_check(
        self,
        check_name: str,
    ) -> Result[HealthCheckPayload, AdminError]:
        """Render health check for admin core.

        Args:
            check_name: Name of the health check.

        Returns:
            Ok(HealthCheckPayload) with the core status, or
            Err(AdminError) when the check is unknown.
        """
        if check_name == "admin_core":
            return Ok(
                HealthCheckPayload(
                    status=HealthStatus.HEALTHY,
                    component="Admin Core",
                    detail="Admin Core Operational",
                )
            )
        return Err(AdminError(f"Unknown health check: {check_name}"))


__all__ = ["CoreAdminContributor"]
