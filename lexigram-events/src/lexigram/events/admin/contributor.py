"""Admin contributor for lexigram-events — surfaces event throughput and
dead-letter widgets into the Lexigram admin dashboard.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from lexigram.contracts.admin.contributor import BaseAdminContributor
from lexigram.contracts.admin.errors import AdminError, WidgetNotFoundError
from lexigram.contracts.admin.types import (
    AdminActionDefinition,
    AdminHealthDefinition,
    AdminRouteSpec,
    DashboardWidgetDefinition,
    ManagementPageDefinition,
    NavigationContribution,
    PageCategory,
    WidgetCategory,
    WidgetKind,
    WidgetParams,
    WidgetSize,
    WidgetViewModel,
)
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result

if TYPE_CHECKING:
    from lexigram.contracts.admin.widget_protocols import WidgetHandlerProtocol
    from lexigram.contracts.core.di import ContainerResolverProtocol


async def _empty_handler(request: object) -> str:  # noqa: ARG001
    """Placeholder handler for contributed routes."""
    return ""


logger = get_logger(__name__)

_WIDGETS: tuple[DashboardWidgetDefinition, ...] = (
    DashboardWidgetDefinition(
        name="events_throughput",
        title="Events Throughput",
        contributor="events",
        render_endpoint="/admin/events/widgets/events_throughput",
        size=WidgetSize.LARGE,
        category=WidgetCategory.METRICS,
        view_kind=WidgetKind.STAT,
        description="Domain events published and consumed per second.",
    ),
    DashboardWidgetDefinition(
        name="dead_letter_count",
        title="Dead-Letter Count",
        contributor="events",
        render_endpoint="/admin/events/widgets/dead_letter_count",
        size=WidgetSize.SMALL,
        category=WidgetCategory.HEALTH,
        view_kind=WidgetKind.HEALTH,
        description="Number of events currently sitting in the dead-letter queue.",
    ),
)

_NAV_ITEMS: tuple[NavigationContribution, ...] = (
    NavigationContribution(
        label="Events",
        url="/admin/events",
        icon="bell",
        group="infrastructure",
        order=30,
        children=(
            NavigationContribution(
                label="History",
                url="/admin/events/history",
                icon="clock",
                group="infrastructure",
                order=10,
            ),
            NavigationContribution(
                label="Dead Letter",
                url="/admin/events/dead-letter",
                icon="alert-triangle",
                group="infrastructure",
                order=20,
            ),
        ),
    ),
)

_HEALTH_DEFS: tuple[AdminHealthDefinition, ...] = (
    AdminHealthDefinition(
        name="events.bus",
        contributor="events",
        component="Event Bus",
        check_endpoint="/admin/events/health/bus",
        description="Verifies the event bus is operational and processing events.",
    ),
)

_ACTIONS: tuple[AdminActionDefinition, ...] = (
    AdminActionDefinition(
        name="replay_dead_letter",
        title="Replay Dead-Letter Events",
        contributor="events",
        handler="lexigram.events.admin.actions:replay_dead_letter",
        icon="refresh-cw",
        category="operations",
    ),
)


class EventsAdminContributor(BaseAdminContributor):
    """Admin contributor for the lexigram-events package.

    Surfaces two widgets: events throughput and dead-letter count.
    Each widget is handled by a dedicated handler class that returns
    structured WidgetContent directly.
    Dependencies are resolved from the container in ``on_admin_boot``.
    """

    name = "events"
    display_name = "Events"
    group = "infrastructure"
    icon = "bell"
    priority = 30

    def __init__(self) -> None:
        self._throughput_handler: WidgetHandlerProtocol | None = None
        self._dead_letter_handler: WidgetHandlerProtocol | None = None

    async def on_admin_boot(self, container: ContainerResolverProtocol) -> None:
        """Resolve event admin dependencies from the DI container.

        Args:
            container: The DI container resolver.
        """
        if container is None:
            return
        from lexigram.events.admin.handlers.dead_letter_count import (
            DeadLetterCountWidgetHandler,
        )
        from lexigram.events.admin.handlers.events_throughput import (
            EventsThroughputWidgetHandler,
        )

        try:
            self._throughput_handler = await container.resolve(
                EventsThroughputWidgetHandler
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "events_contributor.throughput_handler_unavailable", error=str(exc)
            )
            self._throughput_handler = None

        try:
            self._dead_letter_handler = await container.resolve(
                DeadLetterCountWidgetHandler
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "events_contributor.dead_letter_handler_unavailable", error=str(exc)
            )
            self._dead_letter_handler = None

    def get_routes(self) -> Sequence[AdminRouteSpec]:
        return [
            AdminRouteSpec(
                path=w.render_endpoint,
                method="GET",
                handler=_empty_handler,
                name=f"widgets.{w.name}",
            )
            for w in _WIDGETS
        ]

    def get_dashboard_widgets(self) -> Sequence[DashboardWidgetDefinition]:
        return list(_WIDGETS)

    def get_navigation_items(self) -> Sequence[NavigationContribution]:
        return list(_NAV_ITEMS)

    def get_health_definitions(self) -> Sequence[AdminHealthDefinition]:
        return list(_HEALTH_DEFS)

    def get_actions(self) -> Sequence[AdminActionDefinition]:
        return list(_ACTIONS)

    def get_management_pages(self) -> Sequence[ManagementPageDefinition]:
        return [
            ManagementPageDefinition(
                name="events_overview",
                title="Events Overview",
                contributor="events",
                route_path="/events",
                handler="lexigram.events.admin.pages.overview:EventsOverviewPage",
                category=PageCategory.INFRASTRUCTURE,
                icon="bell",
                description="Event bus overview and throughput metrics",
                order=10,
            ),
            ManagementPageDefinition(
                name="events_history",
                title="Events History",
                contributor="events",
                route_path="/events/history",
                handler="lexigram.events.admin.pages.history:EventsHistoryPage",
                category=PageCategory.INFRASTRUCTURE,
                icon="clock",
                description="Recent event history from the event store",
                order=20,
            ),
            ManagementPageDefinition(
                name="events_dead_letter",
                title="Events Dead Letter",
                contributor="events",
                route_path="/events/dead-letter",
                handler="lexigram.events.admin.pages.dead_letter:EventsDeadLetterPage",
                category=PageCategory.INFRASTRUCTURE,
                icon="alert-triangle",
                description="Dead-letter queue inspection and management",
                order=30,
            ),
        ]

    async def render_widget(
        self,
        widget_name: str,
        params: WidgetParams,
        resolver: ContainerResolverProtocol | None = None,
    ) -> Result[WidgetViewModel, AdminError]:
        """Render a widget using registry-based dispatch.

        Registry pattern: Look up handler by name, fetch data, pass the
        structured WidgetContent through.
        Infrastructure failures (DB, network) propagate as exceptions.
        Domain failures return Err(AdminError).

        Args:
            widget_name: Name of the widget to render.
            params: Widget request parameters.

        Returns:
            Result containing a WidgetViewModel with structured content
            or AdminError.
        """
        if widget_name == "events_throughput":
            handler = self._throughput_handler
        elif widget_name == "dead_letter_count":
            handler = self._dead_letter_handler
        else:
            handler = None

        if handler is None:
            return Err(WidgetNotFoundError(self.name, widget_name))  # type: ignore[arg-type]

        data_result = await handler.get_data(params)
        if data_result.is_err():
            return Err(data_result.unwrap_err())

        return Ok(WidgetViewModel(content=data_result.unwrap()))


__all__ = ["EventsAdminContributor"]
