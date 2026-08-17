"""Admin contributor for the relay gateway operations surface.

The contributor surfaces channel health, route metrics, active streams,
and runtime policy into the admin dashboard, plus permissioned control
actions (channel drain/enable and stream cancellation).  Definitions
and renderers live in sibling modules under this package; the class
here wires them to the DI container and the admin surface contract.
Dependencies are resolved lazily from the DI container at boot; every
surface renders an explicit unavailable state when a dependency is
missing.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, cast

from lexigram.ai.relay.gateway.admin.contributor_actions import (
    ACTIONS as _ACTIONS,
)
from lexigram.ai.relay.gateway.admin.contributor_actions import (
    execute_action as _execute_action,
)
from lexigram.ai.relay.gateway.admin.contributor_actions import (
    load_action_handlers as _load_action_handlers,
)
from lexigram.ai.relay.gateway.admin.contributor_health import (
    HEALTH_DEFS,
)
from lexigram.ai.relay.gateway.admin.contributor_health import (
    render_health_check as _render_health_check,
)
from lexigram.ai.relay.gateway.admin.contributor_widgets import (
    WIDGETS,
    active_streams_content,
    channel_health_content,
    route_activity_content,
)
from lexigram.ai.relay.gateway.operations.controls import (
    PERMISSION_CHANNEL_CONTROL,
    PERMISSION_CHANNEL_MANAGE,
    PERMISSION_POLICY_CONTROL,
    PERMISSION_READ,
    RelayControlsService,
)
from lexigram.ai.relay.gateway.operations.health import RelayHealthService
from lexigram.ai.relay.gateway.operations.metrics import RelayMetricsService
from lexigram.contracts.admin.contributor import BaseAdminContributor
from lexigram.contracts.admin.errors import WidgetNotFoundError
from lexigram.contracts.admin.health_payload import HealthCheckPayload
from lexigram.contracts.admin.types import (
    AdminActionDefinition,
    AdminHealthDefinition,
    DashboardWidgetDefinition,
    ManagementPageDefinition,
    NavigationContribution,
    PageCategory,
    WidgetParams,
    WidgetViewModel,
)
from lexigram.contracts.exceptions.container import ContainerError
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result

if TYPE_CHECKING:
    from lexigram.contracts.admin.errors import AdminError

__all__ = ["RelayGatewayAdminContributor"]

logger = get_logger(__name__)

_NAV_ITEMS: tuple[NavigationContribution, ...] = (
    NavigationContribution(
        label="Relay Gateway",
        url="/admin/relay-gateway/overview",
        icon="shuffle",
        group="ai",
        order=30,
        permission=PERMISSION_READ,
        children=(
            NavigationContribution(
                label="Overview",
                url="/admin/relay-gateway/overview",
                icon="gauge",
                group="ai",
                order=10,
                permission=PERMISSION_READ,
            ),
            NavigationContribution(
                label="Routes",
                url="/admin/relay-gateway/routes",
                icon="activity",
                group="ai",
                order=20,
                permission=PERMISSION_READ,
            ),
            NavigationContribution(
                label="Channels",
                url="/admin/relay-gateway/channels",
                icon="server",
                group="ai",
                order=25,
                permission=PERMISSION_READ,
            ),
            NavigationContribution(
                label="Streams",
                url="/admin/relay-gateway/streams",
                icon="radio",
                group="ai",
                order=30,
                permission=PERMISSION_READ,
            ),
            NavigationContribution(
                label="Settings",
                url="/admin/relay-gateway/settings",
                icon="settings",
                group="ai",
                order=40,
                permission=PERMISSION_READ,
            ),
        ),
    ),
)


class RelayGatewayAdminContributor(BaseAdminContributor):
    """Admin contributor for the relay gateway.

    Provides channel-health and route-activity widgets, management
    pages for overview, routes, streams, and settings, and two
    permissioned operations actions.  Registered via the
    ``lexigram.admin.contributors`` entry point.
    """

    name = "relay-gateway"
    display_name = "Relay Gateway"
    group = "ai"
    icon = "shuffle"
    priority = 57

    required_permissions = frozenset(
        {
            PERMISSION_READ,
            PERMISSION_CHANNEL_CONTROL,
            PERMISSION_CHANNEL_MANAGE,
            PERMISSION_POLICY_CONTROL,
        }
    )

    def __init__(self) -> None:
        self._container: Any = None
        self._health: RelayHealthService | None = None
        self._metrics: RelayMetricsService | None = None
        self._controls: RelayControlsService | None = None
        self._action_handlers: dict[str, Any] = {}

    async def on_admin_boot(self, container: Any) -> None:
        """Resolve relay services from the DI container.

        Widgets that depend on a missing service render an explicit
        unavailable ``MessageContent`` state rather than failing
        the whole admin boot — but the resolution failure itself is
        always logged so it isn't silently invisible in production.

        Args:
            container: The DI container resolver.
        """
        self._container = container
        try:
            self._health = await container.resolve(RelayHealthService)
        except ContainerError:
            logger.warning(
                "relay_gateway.dependency_unavailable",
                dependency="RelayHealthService",
            )
            self._health = None
        try:
            self._metrics = await container.resolve(RelayMetricsService)
        except ContainerError:
            logger.warning(
                "relay_gateway.dependency_unavailable",
                dependency="RelayMetricsService",
            )
            self._metrics = None
        try:
            self._controls = await container.resolve(RelayControlsService)
        except ContainerError:
            logger.warning(
                "relay_gateway.dependency_unavailable",
                dependency="RelayControlsService",
            )
            self._controls = None
        self._action_handlers = _load_action_handlers(_ACTIONS)

    def get_dashboard_widgets(self) -> Sequence[DashboardWidgetDefinition]:
        return list(WIDGETS)

    def get_navigation_items(self) -> Sequence[NavigationContribution]:
        return list(_NAV_ITEMS)

    def get_health_definitions(self) -> Sequence[AdminHealthDefinition]:
        return list(HEALTH_DEFS)

    def get_actions(self) -> Sequence[AdminActionDefinition]:
        return list(_ACTIONS)

    async def execute_action(
        self,
        action_name: str,
        params: dict[str, object],
    ) -> object:
        """Dispatch an action to its boot-resolved handler.

        Handlers run with the container captured at boot; a container is
        required.  Every handler performs server-side parameter
        validation before invoking the control service.

        Args:
            action_name: Name of the action to execute.
            params: Parameters forwarded to the action handler.

        Returns:
            The handler's result mapping.

        Raises:
            LookupError: Unknown action name.
            RuntimeError: Contributor booted without a container.
        """
        return await _execute_action(
            self._action_handlers,
            self._container,
            action_name,
            params,
        )

    def get_management_pages(self) -> Sequence[ManagementPageDefinition]:
        return [
            ManagementPageDefinition(
                name="relay_gateway_overview",
                title="Relay Gateway Overview",
                contributor="relay-gateway",
                route_path="/relay-gateway/overview",
                handler="lexigram.ai.relay.gateway.admin.pages:RelayGatewayOverviewPage",
                category=PageCategory.AI,
                icon="shuffle",
                description="Gateway channels, converters, and active streams",
                order=10,
            ),
            ManagementPageDefinition(
                name="relay_gateway_routes",
                title="Relay Routes",
                contributor="relay-gateway",
                route_path="/relay-gateway/routes",
                handler="lexigram.ai.relay.gateway.admin.pages:RelayGatewayRoutesPage",
                category=PageCategory.AI,
                icon="activity",
                description="Per-route conversion and failure metrics",
                order=20,
            ),
            ManagementPageDefinition(
                name="relay_gateway_streams",
                title="Relay Streams",
                contributor="relay-gateway",
                route_path="/relay-gateway/streams",
                handler="lexigram.ai.relay.gateway.admin.pages:RelayGatewayStreamsPage",
                category=PageCategory.AI,
                icon="radio",
                description="In-flight upstream streams",
                order=30,
            ),
            ManagementPageDefinition(
                name="relay_gateway_settings",
                title="Relay Settings",
                contributor="relay-gateway",
                route_path="/relay-gateway/settings",
                handler="lexigram.ai.relay.gateway.admin.pages:RelayGatewaySettingsPage",
                category=PageCategory.AI,
                icon="settings",
                description="Runtime routing policy",
                order=40,
            ),
            ManagementPageDefinition(
                name="relay_gateway_channels",
                title="Relay Channels",
                contributor="relay-gateway",
                route_path="/relay-gateway/channels",
                handler="lexigram.ai.relay.gateway.admin.pages:RelayGatewayChannelsPage",
                category=PageCategory.AI,
                icon="server",
                description="Durable channel rows",
                order=45,
            ),
        ]

    async def render_widget(
        self,
        widget_name: str,
        params: WidgetParams,
        resolver: Any = None,
    ) -> Result[WidgetViewModel, AdminError]:
        """Render a named widget using handler registry dispatch.

        Args:
            widget_name: Name of the widget to render.
            params: Typed widget parameters.
            resolver: Optional container override; unused, services were
                resolved at boot.

        Returns:
            Ok(WidgetViewModel) with structured content on success;
            Err(WidgetNotFoundError) for unknown widget names.
        """
        renderers: dict[str, tuple[Any, str]] = {
            "channel_health": (channel_health_content, "_health"),
            "route_activity": (route_activity_content, "_metrics"),
            "active_streams": (active_streams_content, "_controls"),
        }
        entry = renderers.get(widget_name)
        if entry is None:
            not_found: Result[WidgetViewModel, AdminError] = cast(
                "Result[WidgetViewModel, AdminError]",
                Err(WidgetNotFoundError("relay-gateway", widget_name)),
            )
            return not_found
        renderer, service_attr = entry
        content = await renderer(getattr(self, service_attr), params)
        return Ok(WidgetViewModel(content=content))

    async def render_health_check(
        self,
        check_name: str,
    ) -> Result[HealthCheckPayload, AdminError]:
        """Render the aggregate channel health check.

        Args:
            check_name: Name of the health check; only
                ``relay.channels`` is served.

        Returns:
            Ok(HealthCheckPayload) with the aggregate snapshot; Err when
            the check is unknown or the health service is unavailable.
        """
        return await _render_health_check(self._health, check_name)
