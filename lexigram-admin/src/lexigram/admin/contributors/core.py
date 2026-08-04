"""Core admin contributor — built-in dashboard surfaces."""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Sequence
from importlib.metadata import PackageNotFoundError, version
import os
import platform
from typing import TYPE_CHECKING, Any, cast

from lexigram.admin.realtime import AdminEvent, SubjectAdminEventHub
from lexigram.contracts.admin import (
    ChartContent,
    ChartPoint,
    EmptyContent,
    HealthOverviewProtocol,
    MetricsReadbackProtocol,
    NamedHealthCheckProtocol,
    PageContent,
    SettingsPanelDefinition,
    Stat,
    StatContent,
    TableCell,
    TableContent,
    Tone,
)
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
from lexigram.logging import get_logger
from lexigram.result import Err, Ok

if TYPE_CHECKING:
    from lexigram.contracts.core.di import ContainerResolverProtocol

logger = get_logger(__name__)


def _status_from_value(value: object) -> HealthStatus:
    """Map a raw status string to a :class:`HealthStatus` member.

    Args:
        value: Raw status string (any case) or enum.

    Returns:
        The matching ``HealthStatus``, or ``UNKNOWN`` when unrecognized.
    """
    status_value = str(value).lower()
    if status_value in {"healthy", "degraded", "unhealthy"}:
        return HealthStatus(status_value)
    return HealthStatus.UNKNOWN


def _framework_version() -> str:
    """Return the installed lexigram core package version, or 'unknown'."""
    try:
        return version("lexigram")
    except PackageNotFoundError:
        return "unknown"


class _SystemInfoPageHandler:
    """Read-only diagnostics panel — proves out the ``get_settings_panels()`` path."""

    def __init__(self, health: object | None) -> None:
        self._health = health

    async def handle(self, request: Any) -> PageContent:
        """Render framework, runtime, and health diagnostics as a table."""
        health_status = "unknown"
        if isinstance(self._health, HealthOverviewProtocol):
            payload, _details = await self._health.run_all()
            health_status = str(getattr(payload, "value", "unknown"))

        rows = (
            (TableCell(text="Framework Version"), TableCell(text=_framework_version())),
            (
                TableCell(text="Python Version"),
                TableCell(text=platform.python_version()),
            ),
            (
                TableCell(text="Environment"),
                TableCell(text=os.environ.get("ENVIRONMENT", "unknown")),
            ),
            (
                TableCell(text="Log Level"),
                TableCell(text=os.environ.get("LOG_LEVEL", "INFO")),
            ),
            (TableCell(text="Health Status"), TableCell(text=health_status)),
        )
        return PageContent(
            title="System Info",
            body=TableContent(columns=("Field", "Value"), rows=rows),
        )


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

    def __init__(
        self,
        *,
        health: object | None = None,
        metrics: object | None = None,
        hub: SubjectAdminEventHub | None = None,
    ) -> None:
        self._container: ContainerResolverProtocol | None = None
        self._health = health
        self._metrics = metrics
        self._hub = hub
        self._activity_cache: deque[AdminEvent] = deque(maxlen=50)
        self._background_tasks: set[asyncio.Task[Any]] = set()
        self._start_activity_tail()

    async def on_admin_boot(self, container: object) -> None:
        self._container = container  # type: ignore[assignment]
        if container is None:
            return
        typed_container = cast("ContainerResolverProtocol", container)
        try:
            if self._health is None:
                self._health = await typed_container.resolve_optional(
                    HealthOverviewProtocol
                )
            if self._metrics is None:
                self._metrics = await typed_container.resolve_optional(
                    MetricsReadbackProtocol
                )
            if self._hub is None:
                self._hub = await typed_container.resolve_optional(SubjectAdminEventHub)
                self._start_activity_tail()
        except Exception as exc:  # noqa: BLE001
            logger.warning("admin.core_sources_unavailable", error=str(exc))

    async def on_admin_shutdown(self) -> None:
        """Cancel the background activity tail, then mark the contributor down."""
        for task in self._background_tasks:
            task.cancel()
        self._background_tasks.clear()

    def _start_activity_tail(self) -> None:
        """Tail broadcast admin events into a bounded cache for the activity widget.

        Broadcast-only: ``subscribe()`` with no ``user_id`` sees only
        events published without ``target_users``, so per-admin
        notifications never leak into the shared dashboard. Requires a
        running event loop; without one (sync construction) the tail
        starts during ``on_admin_boot`` instead.
        """
        if self._hub is None:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        task = loop.create_task(self._drain_activity())
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def _drain_activity(self) -> None:
        if self._hub is None:
            return
        async for event in self._hub.subscribe():
            self._activity_cache.append(event)

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
                view_kind=WidgetKind.TABLE,
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

    def get_settings_panels(self) -> Sequence[SettingsPanelDefinition]:
        """Contribute the read-only System Info diagnostics panel."""
        return [
            SettingsPanelDefinition(
                name="system-info",
                title="System Info",
                contributor=self.package_source,
                route_path="/admin/system/info",
                handler=_SystemInfoPageHandler(self._health),
                icon="info",
                category="System",
                order=10,
            )
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
            if not isinstance(self._health, HealthOverviewProtocol):
                return self._empty("Health overview", "No health monitor registered.")
            _payload, details = await self._health.run_all()
            checks = [
                *details.get("liveness", {}).get("checks", []),
                *details.get("readiness", {}).get("checks", []),
            ]
            healthy = sum(
                1
                for c in checks
                if str(c.get("status")).lower() == HealthStatus.HEALTHY.value
            )
            total = max(len(checks), 1)
            status_value = getattr(_payload, "value", "unknown")
            return cast(
                "Result[WidgetViewModel, AdminError]",
                Ok(
                    WidgetViewModel(
                        content=StatContent(
                            stats=(
                                Stat(label="Health", value=str(status_value)),
                                Stat(label="Checks", value=f"{healthy}/{total}"),
                            )
                        )
                    )
                ),
            )
        if widget_name == "activity":
            if self._hub is None and resolver is not None:
                try:
                    self._hub = await resolver.resolve(SubjectAdminEventHub)
                    self._start_activity_tail()
                except Exception:  # noqa: BLE001 — hub is optional
                    self._hub = None
            rows: list[tuple[TableCell, TableCell, TableCell]] = []
            for event in list(self._activity_cache):
                rows.append(
                    (
                        TableCell(text=str(event.event_type)),
                        TableCell(text=str(event.resource_type or "")),
                        TableCell(
                            text=str(
                                event.resource_id
                                if event.resource_id is not None
                                else ""
                            )
                        ),
                    )
                )
            if not rows:
                return cast(
                    "Result[WidgetViewModel, AdminError]",
                    Ok(
                        WidgetViewModel(
                            content=EmptyContent(
                                title="Recent activity",
                                message="No admin activity yet.",
                            )
                        )
                    ),
                )
            return cast(
                "Result[WidgetViewModel, AdminError]",
                Ok(
                    WidgetViewModel(
                        content=TableContent(
                            columns=("Event", "Resource", "ID"),
                            rows=tuple(rows),
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
        if not isinstance(self._metrics, MetricsReadbackProtocol):
            return ChartContent(
                points=(
                    ChartPoint(
                        label="Not measured",
                        value=0.0,
                        tone=Tone.WARNING,
                    ),
                )
            )
        points: list[ChartPoint] = []
        for name, metric in self._metrics.get_all_metrics().items():
            value = getattr(metric, "get_value", lambda: 0.0)()
            points.append(
                ChartPoint(
                    label=name,
                    value=float(value),
                    tone=Tone.SUCCESS if float(value) >= 0 else Tone.DANGER,
                )
            )
        if not points:
            metric = self._metrics.get_metric("requests_total")
            if metric is not None:
                points.append(
                    ChartPoint(
                        label="requests_total",
                        value=float(getattr(metric, "get_value", lambda: 0.0)()),
                        tone=Tone.DEFAULT,
                    )
                )
        return ChartContent(points=tuple(points))

    def _empty(self, title: str, message: str) -> Result[WidgetViewModel, AdminError]:
        """Return the empty-content placeholder shape.

        Args:
            title: Placeholder title.
            message: Placeholder message.

        Returns:
            Ok containing a WidgetViewModel with EmptyContent.
        """
        return cast(
            "Result[WidgetViewModel, AdminError]",
            Ok(WidgetViewModel(content=EmptyContent(title=title, message=message))),
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
            if not isinstance(self._health, HealthOverviewProtocol):
                return Ok(
                    HealthCheckPayload(
                        status=HealthStatus.UNKNOWN,
                        component="Admin Core",
                        detail="No health registry registered.",
                    )
                )
            payload, _details = await self._health.run_all()
            status = _status_from_value(getattr(payload, "value", "unknown"))
            return Ok(
                HealthCheckPayload(
                    status=status,
                    component="Admin Core",
                    detail=(
                        "Admin Core operational"
                        if status == HealthStatus.HEALTHY
                        else "Admin Core degraded"
                    ),
                )
            )
        if not isinstance(self._health, NamedHealthCheckProtocol):
            return Ok(
                HealthCheckPayload(
                    status=HealthStatus.UNKNOWN,
                    component="Admin Core",
                    detail="No health registry registered.",
                )
            )
        result = await self._health.run_check(check_name)
        status_value = str(result.get("status", "UNKNOWN"))
        return Ok(
            HealthCheckPayload(
                status=_status_from_value(status_value),
                component=str(result.get("component", check_name)),
                detail=str(
                    result.get("error")
                    or f"{result.get('component', check_name)} checked"
                ),
            )
        )


__all__ = ["CoreAdminContributor"]
