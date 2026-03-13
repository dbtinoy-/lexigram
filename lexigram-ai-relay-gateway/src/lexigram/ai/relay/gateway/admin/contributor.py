"""Admin contributor for the relay gateway operations surface.

The contributor surfaces channel health, route metrics, active streams,
and runtime policy into the admin dashboard, plus permissioned control
actions (channel drain/enable and stream cancellation).  Dependencies
are resolved lazily from the DI container at boot; every surface
renders an explicit unavailable state when a dependency is missing.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, cast

from lexigram.ai.relay.gateway.operations.controls import (
    PERMISSION_CHANNEL_CONTROL,
    PERMISSION_CHANNEL_MANAGE,
    PERMISSION_POLICY_CONTROL,
    PERMISSION_READ,
    PERMISSION_STREAM_CONTROL,
    RelayControlsService,
)
from lexigram.ai.relay.gateway.operations.health import RelayHealthService
from lexigram.ai.relay.gateway.operations.metrics import RelayMetricsService
from lexigram.contracts.admin.contributor import BaseAdminContributor
from lexigram.contracts.admin.errors import (
    HealthCheckNotFoundError,
    WidgetNotFoundError,
)
from lexigram.contracts.admin.route_spec import AdminRouteSpec
from lexigram.contracts.admin.types import (
    ActionParameterField,
    ActionParameterSchema,
    AdminActionDefinition,
    AdminHealthDefinition,
    DashboardWidgetDefinition,
    ManagementPageDefinition,
    NavigationContribution,
    PageCategory,
    WidgetCategory,
    WidgetParams,
    WidgetSize,
    WidgetViewModel,
)
from lexigram.contracts.ai.relay import RelayGatewayError, TimeWindow
from lexigram.primitives import clock
from lexigram.result import Err, Ok, Result
from lexigram.ui import Card, el, render_to_string

if TYPE_CHECKING:
    from lexigram.contracts.admin.errors import AdminError

__all__ = ["RelayGatewayAdminContributor"]

_WIDGETS: tuple[DashboardWidgetDefinition, ...] = (
    DashboardWidgetDefinition(
        name="channel_health",
        title="Channel Health",
        contributor="relay-gateway",
        render_endpoint="/admin/relay-gateway/widgets/channel_health",
        size=WidgetSize.LARGE,
        category=WidgetCategory.HEALTH,
        refresh_interval_seconds=15,
        permission=PERMISSION_READ,
        icon="heart-pulse",
        description="Per-channel health snapshots from probe status.",
    ),
    DashboardWidgetDefinition(
        name="route_activity",
        title="Route Activity",
        contributor="relay-gateway",
        render_endpoint="/admin/relay-gateway/widgets/route_activity",
        size=WidgetSize.LARGE,
        category=WidgetCategory.METRICS,
        refresh_interval_seconds=30,
        permission=PERMISSION_READ,
        icon="activity",
        description="Per-route conversion and failure metrics.",
    ),
    DashboardWidgetDefinition(
        name="active_streams",
        title="Active Streams",
        contributor="relay-gateway",
        render_endpoint="/admin/relay-gateway/widgets/active_streams",
        size=WidgetSize.MEDIUM,
        category=WidgetCategory.METRICS,
        refresh_interval_seconds=10,
        permission=PERMISSION_READ,
        icon="radio",
        description="In-flight upstream streams, oldest first.",
    ),
)

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

_HEALTH_DEFS: tuple[AdminHealthDefinition, ...] = (
    AdminHealthDefinition(
        name="relay.channels",
        contributor="relay-gateway",
        component="Relay Channels",
        check_endpoint="/admin/relay-gateway/health/channels",
        description="Aggregates per-channel probe status.",
    ),
)

_ACTIONS: tuple[AdminActionDefinition, ...] = (
    AdminActionDefinition(
        name="set_channel_state",
        title="Set Channel State",
        contributor="relay-gateway",
        handler="lexigram.ai.relay.gateway.admin.actions:set_channel_state",
        icon="toggle-right",
        confirmation_message="Enable or drain this channel for new requests?",
        category="operations",
        permission=PERMISSION_CHANNEL_CONTROL,
        parameter_schema=ActionParameterSchema(
            fields=(
                ActionParameterField(
                    name="channel",
                    type_hint="str",
                    required=True,
                    description="Channel name from the gateway channel table.",
                ),
                ActionParameterField(
                    name="enabled",
                    type_hint="bool",
                    required=True,
                    description="Whether the channel accepts new requests.",
                ),
            ),
            description="Enable or drain a gateway channel.",
        ),
    ),
    AdminActionDefinition(
        name="force_cancel_stream",
        title="Force Cancel Stream",
        contributor="relay-gateway",
        handler="lexigram.ai.relay.gateway.admin.actions:force_cancel_stream",
        icon="x-circle",
        confirmation_message="This terminates the upstream request immediately.",
        destructive=True,
        category="operations",
        permission=PERMISSION_STREAM_CONTROL,
        parameter_schema=ActionParameterSchema(
            fields=(
                ActionParameterField(
                    name="stream_id",
                    type_hint="str",
                    required=True,
                    description="Identifier of the stream session to cancel.",
                ),
            ),
        ),
    ),
    AdminActionDefinition(
        name="create_channel",
        title="Create Channel",
        contributor="relay-gateway",
        handler="lexigram.ai.relay.gateway.admin.actions:create_channel",
        icon="plus-circle",
        confirmation_message="Create a durable relay channel?",
        category="operations",
        permission=PERMISSION_CHANNEL_MANAGE,
        parameter_schema=ActionParameterSchema(
            fields=(
                ActionParameterField(
                    name="name",
                    type_hint="str",
                    required=True,
                    description="Unique channel name.",
                ),
                ActionParameterField(
                    name="upstream_base_url",
                    type_hint="str",
                    required=True,
                    description="Upstream endpoint base URL.",
                ),
                ActionParameterField(
                    name="target_format",
                    type_hint="str",
                    required=True,
                    description=(
                        "Wire format: openai_chat, openai_responses, claude, or gemini."
                    ),
                ),
                ActionParameterField(
                    name="models",
                    type_hint="str",
                    required=True,
                    description="Comma-separated model aliases.",
                ),
                ActionParameterField(
                    name="priority",
                    type_hint="int",
                    required=False,
                    default=100,
                    description="Selection priority (lower routes first).",
                ),
                ActionParameterField(
                    name="weight",
                    type_hint="int",
                    required=False,
                    default=100,
                    description="Load-balancing weight.",
                ),
                ActionParameterField(
                    name="enabled",
                    type_hint="bool",
                    required=False,
                    default=True,
                    description="Whether the channel accepts new requests.",
                ),
                ActionParameterField(
                    name="timeout_seconds",
                    type_hint="float",
                    required=False,
                    default=60.0,
                    description="Upstream timeout in seconds.",
                ),
            ),
            description="Create a durable gateway channel.",
        ),
    ),
    AdminActionDefinition(
        name="update_channel",
        title="Update Channel",
        contributor="relay-gateway",
        handler="lexigram.ai.relay.gateway.admin.actions:update_channel",
        icon="pencil",
        confirmation_message="Update this durable channel at the given revision?",
        category="operations",
        permission=PERMISSION_CHANNEL_MANAGE,
        parameter_schema=ActionParameterSchema(
            fields=(
                ActionParameterField(
                    name="name",
                    type_hint="str",
                    required=True,
                    description="Channel name to update.",
                ),
                ActionParameterField(
                    name="expected_revision",
                    type_hint="int",
                    required=True,
                    description="Revision the caller observed; stale writes are rejected.",
                ),
                ActionParameterField(
                    name="upstream_base_url",
                    type_hint="str",
                    required=True,
                    description="Upstream endpoint base URL.",
                ),
                ActionParameterField(
                    name="target_format",
                    type_hint="str",
                    required=True,
                    description="Wire format: openai_chat, openai_responses, claude, or gemini.",
                ),
                ActionParameterField(
                    name="models",
                    type_hint="str",
                    required=True,
                    description="Comma-separated model aliases.",
                ),
                ActionParameterField(
                    name="priority",
                    type_hint="int",
                    required=False,
                    default=100,
                    description="Selection priority (lower routes first).",
                ),
                ActionParameterField(
                    name="weight",
                    type_hint="int",
                    required=False,
                    default=100,
                    description="Load-balancing weight.",
                ),
                ActionParameterField(
                    name="enabled",
                    type_hint="bool",
                    required=False,
                    default=True,
                    description="Whether the channel accepts new requests.",
                ),
                ActionParameterField(
                    name="timeout_seconds",
                    type_hint="float",
                    required=False,
                    default=60.0,
                    description="Upstream timeout in seconds.",
                ),
            ),
            description="Update a durable gateway channel under compare-and-set.",
        ),
    ),
    AdminActionDefinition(
        name="delete_channel",
        title="Delete Channel",
        contributor="relay-gateway",
        handler="lexigram.ai.relay.gateway.admin.actions:delete_channel",
        icon="trash-2",
        confirmation_message="Delete this channel permanently?",
        destructive=True,
        category="operations",
        permission=PERMISSION_CHANNEL_MANAGE,
        parameter_schema=ActionParameterSchema(
            fields=(
                ActionParameterField(
                    name="name",
                    type_hint="str",
                    required=True,
                    description="Channel name to delete.",
                ),
                ActionParameterField(
                    name="expected_revision",
                    type_hint="int",
                    required=True,
                    description="Revision the caller observed; stale deletes are rejected.",
                ),
            ),
            description="Delete a durable gateway channel under compare-and-set.",
        ),
    ),
    AdminActionDefinition(
        name="test_channel",
        title="Test Channel",
        contributor="relay-gateway",
        handler="lexigram.ai.relay.gateway.admin.actions:test_channel",
        icon="activity",
        confirmation_message="Probe this channel through the health service?",
        category="operations",
        permission=PERMISSION_CHANNEL_MANAGE,
        parameter_schema=ActionParameterSchema(
            fields=(
                ActionParameterField(
                    name="name",
                    type_hint="str",
                    required=True,
                    description="Channel name to probe.",
                ),
            ),
            description="Run the channel health probe and report the verdict.",
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

    async def on_admin_boot(self, container: Any) -> None:
        """Resolve relay services from the DI container.

        Args:
            container: The DI container resolver.
        """
        self._container = container
        try:
            self._health = await container.resolve(RelayHealthService)
        except Exception:
            self._health = None
        try:
            self._metrics = await container.resolve(RelayMetricsService)
        except Exception:
            self._metrics = None
        try:
            self._controls = await container.resolve(RelayControlsService)
        except Exception:
            self._controls = None

    def get_dashboard_widgets(self) -> Sequence[DashboardWidgetDefinition]:
        return list(_WIDGETS)

    def get_navigation_items(self) -> Sequence[NavigationContribution]:
        return list(_NAV_ITEMS)

    def get_health_definitions(self) -> Sequence[AdminHealthDefinition]:
        return list(_HEALTH_DEFS)

    def get_actions(self) -> Sequence[AdminActionDefinition]:
        return list(_ACTIONS)

    async def execute_action(
        self,
        action_name: str,
        params: dict[str, object],
    ) -> object:
        """Dispatch an action to its lazy-loaded handler.

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
        from importlib import import_module as _import_module

        registry = {action.name: action for action in _ACTIONS}
        definition = registry.get(action_name)
        if definition is None:
            raise LookupError(f"unknown relay-gateway action {action_name!r}")
        module_path, _, handler_name = definition.handler.partition(":")
        module = _import_module(module_path)
        handler = getattr(module, handler_name)
        if self._container is None:
            raise RuntimeError("contributor has no container; on_admin_boot required")
        return await handler(self._container, **params)

    def get_routes(self) -> Sequence[AdminRouteSpec]:
        """Return the widget and health render endpoints.

        Returns:
            One route spec per dashboard widget and health check.
        """
        routes: list[AdminRouteSpec] = [
            AdminRouteSpec(
                path=cast("str", w.render_endpoint),
                method="GET",
                handler=_render_for_widget,
                name=f"widgets.{w.name}",
                permissions=frozenset({PERMISSION_READ}),
            )
            for w in _WIDGETS
        ]
        routes += [
            AdminRouteSpec(
                path=cast("str", h.check_endpoint),
                method="GET",
                handler=_render_for_health,
                name=f"health.{h.name}",
                permissions=frozenset({PERMISSION_READ}),
            )
            for h in _HEALTH_DEFS
        ]
        return routes

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
            Ok(WidgetViewModel) with rendered HTML on success;
            Err(WidgetNotFoundError) for unknown widget names.
        """
        renderers = {
            "channel_health": self._render_channel_health,
            "route_activity": self._render_route_activity,
            "active_streams": self._render_active_streams,
        }
        renderer = renderers.get(widget_name)
        if renderer is None:
            not_found: Result[WidgetViewModel, AdminError] = cast(
                "Result[WidgetViewModel, AdminError]",
                Err(WidgetNotFoundError("relay-gateway", widget_name)),
            )
            return not_found
        html = await renderer(params)
        return Ok(WidgetViewModel(body=html))

    async def render_health_check(
        self,
        check_name: str,
    ) -> Result[str, AdminError]:
        """Render the aggregate channel health check.

        Args:
            check_name: Name of the health check; only
                ``relay.channels`` is served.

        Returns:
            Ok(html) with the aggregate snapshot; Err when the check is
            unknown or the health service is unavailable.
        """
        if check_name != "relay.channels":
            not_found: Result[str, AdminError] = cast(
                "Result[str, AdminError]",
                Err(HealthCheckNotFoundError("relay-gateway", check_name)),
            )
            return not_found
        if self._health is None:
            unavailable: Result[str, AdminError] = cast(
                "Result[str, AdminError]",
                Err(HealthCheckNotFoundError("relay-gateway", check_name)),
            )
            return unavailable
        snapshots = await self._health.channel_health()
        parts = [f"{snap.channel}: {snap.status}" for snap in snapshots]
        body = ", ".join(parts) if parts else "no channels configured"
        return Ok(body)

    async def _render_channel_health(self, params: WidgetParams) -> str:
        """Render per-channel health as a status table."""
        if self._health is None:
            return render_to_string(
                _unavailable("Channel health requires RelayHealthService.")
            )
        snapshots = await self._health.channel_health()
        rows = []
        for snap in snapshots:
            badge = _status_badge(snap.status)
            rows.append(
                el(
                    "tr",
                    el("td", snap.channel, class_="py-1.5 pr-3 font-medium"),
                    el("td", snap.target.value, class_="py-1.5 pr-3"),
                    el("td", badge, class_="py-1.5 pr-3"),
                    el("td", str(snap.model_count), class_="py-1.5 pr-3"),
                    el(
                        "td",
                        _ms(snap.latency_ms_p50),
                        class_="py-1.5 pr-3",
                    ),
                    el("td", _details(snap.detail_code), class_="py-1.5"),
                )
            )
        table = _table(
            ["Channel", "Target", "Status", "Models", "P50", "Detail"],
            rows,
        )
        return render_to_string(
            Card(title="Channel Health", content=render_to_string(table))
        )

    async def _render_route_activity(self, params: WidgetParams) -> str:
        """Render routed metrics for the widget window."""
        if self._metrics is None:
            return render_to_string(
                _unavailable("Route metrics service is unavailable.")
            )
        from datetime import timedelta

        window = TimeWindow(
            start=clock.now() - timedelta(minutes=params.time_window_minutes),
            end=clock.now(),
        )
        rows = []
        try:
            routes = await self._metrics.route_metrics(window)
        except RelayGatewayError as exc:
            return render_to_string(_unavailable(exc.message))
        for route in routes:
            badges = (
                el("span", "conv-loss", class_="mr-1"),
                el("span", "stream-fail", class_="mr-1"),
            )
            rows.append(
                el(
                    "tr",
                    el("td", route.source.value, class_="py-1.5 pr-3 font-medium"),
                    el("td", route.target.value, class_="py-1.5 pr-3"),
                    el("td", str(route.request_count), class_="py-1.5 pr-3"),
                    el(
                        "td",
                        str(route.unsupported_count),
                        class_="py-1.5 pr-3",
                    ),
                    el(
                        "td",
                        str(route.stream_failure_count),
                        class_="py-1.5 pr-3",
                    ),
                    el("td", _quality_badge(route.quality.value), class_="py-1.5"),
                )
            )
        empty = el(
            "p",
            "No route activity in this window.",
            class_="text-sm text-[var(--muted-foreground)] py-4",
        )
        table = _table(
            [
                "Route",
                "Target",
                "Requests",
                "Unsupported",
                "Stream Failures",
                "Quality",
            ],
            rows,
        )
        body = render_to_string(table) if rows else render_to_string(empty)
        return render_to_string(Card(title="Route Activity", content=body))

    async def _render_active_streams(self, params: WidgetParams) -> str:
        """Render the in-flight stream registry."""
        if self._controls is None:
            return render_to_string(_unavailable("Controls service is unavailable."))
        streams = self._controls.active_streams()
        if not streams:
            return render_to_string(
                Card(
                    title="Active Streams",
                    content=render_to_string(
                        el(
                            "p",
                            "No streams in flight.",
                            class_="text-sm text-[var(--muted-foreground)] py-4",
                        )
                    ),
                )
            )
        rows = [
            el(
                "tr",
                el("td", s.stream_id, class_="py-1.5 pr-3 font-mono text-xs"),
                el("td", s.channel, class_="py-1.5 pr-3"),
                el("td", s.model, class_="py-1.5 pr-3"),
                el("td", _iso(s.started_at), class_="py-1.5"),
            )
            for s in streams
        ]
        table = _table(["Stream", "Channel", "Model", "Started"], rows)
        return render_to_string(
            Card(title="Active Streams", content=render_to_string(table))
        )


async def _render_for_widget(request: object) -> str:  # noqa: ARG001
    """Placeholder route handler for widget endpoints.

    Widget content is rendered by the admin dashboard through
    ``render_widget``; the route spec only proves registration.
    """
    return ""


async def _render_for_health(request: object) -> str:  # noqa: ARG001
    """Placeholder route handler for health check endpoints.

    Health content is rendered by the admin dashboard through
    ``render_health_check``; the route spec only proves registration.
    """
    return ""


def _unavailable(message: str) -> Any:
    """Render an explicit unavailable dependency message."""
    return Card(
        title="Unavailable",
        content=render_to_string(
            el(
                "p",
                message,
                class_="text-sm text-[var(--muted-foreground)] py-4",
            )
        ),
    )


def _table(headers: list[str], rows: list[Any]) -> Any:
    """Build a styled table element."""
    return el(
        "table",
        el(
            "thead",
            el(
                "tr",
                *[
                    el(
                        "th",
                        h,
                        class_=(
                            "text-left text-xs font-semibold "
                            "text-[var(--muted-foreground)] uppercase tracking-wider "
                            "pb-1 pr-3"
                        ),
                        scope_="col",
                    )
                    for h in headers
                ],
            ),
        ),
        el("tbody", *rows, class_="divide-y divide-[var(--border)]"),
        class_="w-full",
    )


def _status_badge(status: str) -> Any:
    """Render a status badge for a channel health snapshot."""
    colors = {
        "healthy": "bg-green-100 text-green-700",
        "degraded": "bg-yellow-100 text-yellow-700",
        "unavailable": "bg-gray-100 text-gray-500",
        "failed": "bg-red-100 text-red-700",
    }
    return el(
        "span",
        status,
        class_=f"inline-block px-2 py-0.5 rounded text-xs font-medium {colors.get(status, 'bg-gray-100 text-gray-500')}",
    )


def _quality_badge(quality: str) -> Any:
    """Render a conversion quality badge."""
    colors = {
        "native": "bg-green-100 text-green-700",
        "preserved": "bg-blue-100 text-blue-700",
        "lossless": "bg-emerald-100 text-emerald-700",
        "lossy": "bg-yellow-100 text-yellow-700",
        "discouraged": "bg-red-100 text-red-700",
    }
    return el(
        "span",
        quality,
        class_=f"inline-flex px-2 py-0.5 rounded text-xs font-medium {colors.get(quality, 'bg-gray-100 text-gray-500')}",
    )


def _ms(value: float | None) -> str:
    """Format a latency value as milliseconds."""
    return f"{value:.1f} ms" if value is not None else "-"


def _iso(dt: Any) -> str:
    """Format a datetime for display."""
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else "-"


def _details(detail_code: str | None) -> str:
    """Humanize the machine-readable detail code."""
    if detail_code is None:
        return "-"
    return detail_code.replace("_", " ")
