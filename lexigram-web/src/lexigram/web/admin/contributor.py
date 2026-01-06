"""Admin contributor for lexigram-web — surfaces web server widgets, navigation,
health checks, and actions into the Lexigram admin dashboard.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, cast

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
    WidgetParams,
    WidgetSize,
    WidgetViewModel,
)
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result

if TYPE_CHECKING:
    from lexigram.contracts.admin.widget_protocols import WidgetHandlerProtocol
    from lexigram.contracts.core.di import ContainerResolverProtocol
    from lexigram.web.admin.renderer import PackageWidgetRenderer


async def _empty_handler(request: object) -> str:  # noqa: ARG001
    """Placeholder handler for contributed routes."""
    return ""


logger = get_logger(__name__)

_WIDGET_TEMPLATES: dict[str, str] = {
    "server_status": "server_status.html",
    "active_connections": "active_connections.html",
    "request_rate": "request_rate.html",
}

_WIDGETS: tuple[DashboardWidgetDefinition, ...] = (
    DashboardWidgetDefinition(
        name="server_status",
        title="Server Status",
        contributor="web",
        render_endpoint="/admin/web/widgets/server_status",
        size=WidgetSize.SMALL,
        category=WidgetCategory.HEALTH,
        description="Current HTTP server status and uptime.",
    ),
    DashboardWidgetDefinition(
        name="active_connections",
        title="Active Connections",
        contributor="web",
        render_endpoint="/admin/web/widgets/active_connections",
        size=WidgetSize.SMALL,
        category=WidgetCategory.METRICS,
        description="Number of currently open HTTP connections.",
    ),
    DashboardWidgetDefinition(
        name="request_rate",
        title="Request Rate",
        contributor="web",
        render_endpoint="/admin/web/widgets/request_rate",
        size=WidgetSize.SMALL,
        category=WidgetCategory.METRICS,
        description="Incoming requests per second over the last minute.",
    ),
)

_NAV_ITEMS: tuple[NavigationContribution, ...] = (
    NavigationContribution(
        label="Web",
        url="/admin/web",
        icon="globe",
        group="infrastructure",
        order=10,
        children=(
            NavigationContribution(
                label="Routes",
                url="/admin/web/routes",
                icon="map",
                group="infrastructure",
                order=10,
            ),
            NavigationContribution(
                label="Middleware",
                url="/admin/web/middleware",
                icon="layers",
                group="infrastructure",
                order=20,
            ),
        ),
    ),
)

_HEALTH_DEFS: tuple[AdminHealthDefinition, ...] = (
    AdminHealthDefinition(
        name="web.server",
        contributor="web",
        component="HTTP Server",
        check_endpoint="/admin/web/health/server",
        description="Verifies the ASGI server is accepting connections.",
    ),
)

_ACTIONS: tuple[AdminActionDefinition, ...] = (
    AdminActionDefinition(
        name="reload_routes",
        title="Reload Routes",
        contributor="web",
        handler="lexigram.web.admin.actions:reload_routes",
        icon="refresh-cw",
        category="operations",
    ),
)


class WebAdminContributor(BaseAdminContributor):
    """Admin contributor for the lexigram-web package.

    Provides widget rendering with registry-based dispatch to handlers.
    Each widget is handled by a dedicated handler class that implements
    WidgetHandlerProtocol and returns a frozen ViewModel.
    Dependencies are resolved from the container in ``on_admin_boot``.
    """

    name = "web"
    display_name = "Web Server"
    group = "infrastructure"
    icon = "globe"
    priority = 10

    def __init__(self) -> None:
        self._renderer: PackageWidgetRenderer | None = None
        self._handlers: dict[str, WidgetHandlerProtocol] = {}

    async def on_admin_boot(self, container: ContainerResolverProtocol) -> None:
        """Resolve web admin dependencies from the DI container.

        Args:
            container: The DI container resolver.
        """
        if container is None:
            return
        from lexigram.web.admin.handlers.active_connections import (
            ActiveConnectionsWidgetHandler,
        )
        from lexigram.web.admin.handlers.request_rate import (
            RequestRateWidgetHandler,
        )
        from lexigram.web.admin.handlers.server_status import (
            ServerStatusWidgetHandler,
        )
        from lexigram.web.admin.renderer import PackageWidgetRenderer

        try:
            self._renderer = await container.resolve(PackageWidgetRenderer)
        except Exception as exc:  # noqa: BLE001
            logger.warning("web_contributor.renderer_unavailable", error=str(exc))

        try:
            self._handlers = {
                "server_status": await container.resolve(ServerStatusWidgetHandler),
                "active_connections": await container.resolve(
                    ActiveConnectionsWidgetHandler
                ),
                "request_rate": await container.resolve(RequestRateWidgetHandler),
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("web_contributor.handlers_unavailable", error=str(exc))

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
                name="web_overview",
                title="Web Overview",
                contributor="web",
                route_path="/web",
                handler="lexigram.web.admin.pages.overview:WebOverviewPage",
                category=PageCategory.INFRASTRUCTURE,
                icon="globe",
                description="Web server overview and metrics",
                order=10,
            ),
            ManagementPageDefinition(
                name="web_routes",
                title="Web Routes",
                contributor="web",
                route_path="/web/routes",
                handler="lexigram.web.admin.pages.routes:WebRoutesPage",
                category=PageCategory.INFRASTRUCTURE,
                icon="map",
                description="View registered routes",
                order=20,
            ),
            ManagementPageDefinition(
                name="web_middleware",
                title="Web Middleware",
                contributor="web",
                route_path="/web/middleware",
                handler="lexigram.web.admin.pages.middleware:WebMiddlewarePage",
                category=PageCategory.INFRASTRUCTURE,
                icon="layers",
                description="View middleware and filter chains",
                order=30,
            ),
        ]

    async def render_widget(
        self,
        widget_name: str,
        params: WidgetParams,
        **kwargs: Any,
    ) -> Result[WidgetViewModel, AdminError]:
        """Render a widget by name using registry dispatch.

        Registry dispatch — no if/elif. Infrastructure exceptions propagate.

        Args:
            widget_name: Name of the widget to render (e.g. "server_status").
            params: Widget request parameters.

        Returns:
            Result containing rendered HTML string, or WidgetNotFoundError
            if the widget is not registered.
        """
        handler = self._handlers.get(widget_name)
        if handler is None:
            return cast(
                "Result[WidgetViewModel, AdminError]",
                Err(WidgetNotFoundError(self.name, widget_name)),
            )
        if self._renderer is None:
            return cast(
                "Result[WidgetViewModel, AdminError]",
                Err(WidgetNotFoundError(self.name, widget_name)),
            )
        result = await handler.get_data(params)
        if result.is_err():
            return cast("Result[WidgetViewModel, AdminError]", result)
        template = _WIDGET_TEMPLATES[widget_name]
        html = self._renderer.render(template, vars(result.unwrap()))
        return cast(
            "Result[WidgetViewModel, AdminError]",
            Ok(WidgetViewModel(body=html)),
        )


__all__ = ["WebAdminContributor"]
