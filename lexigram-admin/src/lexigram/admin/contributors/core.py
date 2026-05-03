"""Core admin contributor — built-in dashboard surfaces."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, cast

from lexigram.contracts.admin import ChartContent, ChartPoint, EmptyContent, Tone
from lexigram.contracts.admin.contributor import BaseAdminContributor
from lexigram.contracts.admin.errors import AdminError, WidgetNotFoundError
from lexigram.contracts.admin.health_payload import HealthCheckPayload
from lexigram.contracts.admin.types import (
    AdminHealthDefinition,
    DashboardWidgetDefinition,
    NavigationContribution,
    WidgetCategory,
    WidgetKind,
    WidgetParams,
    WidgetSize,
    WidgetViewModel,
)
from lexigram.contracts.core.health import HealthStatus
from lexigram.contracts.core.result import Result
from lexigram.result import Err, Ok

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
                view_kind=WidgetKind.EMPTY,
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
                view_kind=WidgetKind.EMPTY,
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
                view_kind=WidgetKind.CHART,
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
            Result containing a WidgetViewModel with structured ``content``,
            or WidgetNotFoundError if the widget is not found.
        """

        if widget_name == "health":
            # TODO(admin): wire the health widget to a real aggregated
            # health data source instead of the empty placeholder.
            return cast(
                "Result[WidgetViewModel, AdminError]",
                Ok(
                    WidgetViewModel(
                        content=EmptyContent(
                            title="Health overview",
                            message="Not yet wired to a data source.",
                        )
                    )
                ),
            )
        if widget_name == "activity":
            # TODO(admin): wire the activity widget to a real activity
            # event source instead of the empty placeholder.
            return cast(
                "Result[WidgetViewModel, AdminError]",
                Ok(
                    WidgetViewModel(
                        content=EmptyContent(
                            title="Recent activity",
                            message="Not yet wired to a data source.",
                        )
                    )
                ),
            )
        if widget_name == "chart_metrics":
            return cast(
                "Result[WidgetViewModel, AdminError]",
                Ok(WidgetViewModel(content=self._chart_metrics_content())),
            )
        result: Result[WidgetViewModel, AdminError] = cast(
            "Result[WidgetViewModel, AdminError]",
            Err(WidgetNotFoundError(self.name, widget_name)),
        )
        return result

    def _chart_metrics_content(self) -> ChartContent:
        """Return the framework metrics as structured chart content."""
        return ChartContent(
            points=(
                ChartPoint(label="Active Users", value=847, tone=Tone.DEFAULT),
                ChartPoint(label="Requests/min", value=2341, tone=Tone.SUCCESS),
                ChartPoint(label="Error Rate", value=1.2, tone=Tone.DANGER),
                ChartPoint(label="Avg Latency", value=45, tone=Tone.WARNING),
                ChartPoint(label="Memory %", value=68, tone=Tone.INFO),
            )
        )

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
