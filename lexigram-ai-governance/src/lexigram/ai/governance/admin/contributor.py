"""Admin contributor for the AI governance relay accounting surface.

The contributor surfaces relay usage, quota pressure, and settlement
failures from the governance billing stack into the admin dashboard.
Dependencies (the usage store and the reservation manager) are resolved
lazily from the DI container at boot; every surface renders an explicit
unavailable state when a dependency is missing and never reports zero
usage or quota as if it were measured.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import timedelta
from typing import TYPE_CHECKING, Any, cast

from lexigram.ai.governance.relay_billing import (
    RelayReservationManager,
    RelayUsageReport,
    RelayUsageReportService,
)
from lexigram.contracts.admin.contributor import BaseAdminContributor
from lexigram.contracts.admin.errors import (
    HealthCheckNotFoundError,
    WidgetNotFoundError,
)
from lexigram.contracts.admin.health_payload import HealthCheckPayload
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
from lexigram.contracts.ai.governance import RelayUsageStoreProtocol
from lexigram.contracts.core.health import HealthStatus
from lexigram.primitives import clock
from lexigram.result import Err, Ok, Result
from lexigram.ui import Card, el, render_to_string

if TYPE_CHECKING:
    from lexigram.contracts.admin.errors import AdminError

__all__ = ["GovernanceAdminContributor"]

PERMISSION_READ = "governance.read"
PERMISSION_LOG_READ = "relay.logs"
PERMISSION_LEDGER = "relay.billing"

_WIDGETS: tuple[DashboardWidgetDefinition, ...] = (
    DashboardWidgetDefinition(
        name="current_spend",
        title="Current Spend",
        contributor="ai-governance",
        render_endpoint="/admin/ai-governance/widgets/current_spend",
        size=WidgetSize.MEDIUM,
        category=WidgetCategory.RESOURCES,
        refresh_interval_seconds=60,
        permission=PERMISSION_READ,
        icon="dollar-sign",
        description="Total charge settled by the relay billing store.",
    ),
    DashboardWidgetDefinition(
        name="token_dimensions",
        title="Token Dimensions",
        contributor="ai-governance",
        render_endpoint="/admin/ai-governance/widgets/token_dimensions",
        size=WidgetSize.MEDIUM,
        category=WidgetCategory.RESOURCES,
        refresh_interval_seconds=60,
        permission=PERMISSION_READ,
        icon="bar-chart",
        description="Prompt, completion, and total token consumption.",
    ),
    DashboardWidgetDefinition(
        name="quota_pressure",
        title="Quota Pressure",
        contributor="ai-governance",
        render_endpoint="/admin/ai-governance/widgets/quota_pressure",
        size=WidgetSize.SMALL,
        category=WidgetCategory.RESOURCES,
        refresh_interval_seconds=15,
        permission=PERMISSION_READ,
        icon="gauge",
        description="Per-dimension reservation capacity remaining.",
    ),
    DashboardWidgetDefinition(
        name="settlement_failures",
        title="Settlement Failures",
        contributor="ai-governance",
        render_endpoint="/admin/ai-governance/widgets/settlement_failures",
        size=WidgetSize.SMALL,
        category=WidgetCategory.ACTIVITY,
        refresh_interval_seconds=30,
        permission=PERMISSION_READ,
        icon="alert-triangle",
        description="Failed relay settlements in the widget window.",
    ),
)

_NAV_ITEMS: tuple[NavigationContribution, ...] = (
    NavigationContribution(
        label="AI Governance",
        url="/admin/ai-governance/relay-usage",
        icon="shield",
        group="ai",
        order=40,
        permission=PERMISSION_READ,
        children=(
            NavigationContribution(
                label="Relay Usage",
                url="/admin/ai-governance/relay-usage",
                icon="bar-chart",
                group="ai",
                order=10,
                permission=PERMISSION_READ,
            ),
            NavigationContribution(
                label="Relay Quotas",
                url="/admin/ai-governance/relay-quotas",
                icon="gauge",
                group="ai",
                order=20,
                permission=PERMISSION_READ,
            ),
            NavigationContribution(
                label="Relay Settlements",
                url="/admin/ai-governance/relay-settlements",
                icon="receipt",
                group="ai",
                order=30,
                permission=PERMISSION_READ,
            ),
            NavigationContribution(
                label="Request Logs",
                url="/admin/ai-governance/relay-logs",
                icon="list",
                group="ai",
                order=40,
                permission=PERMISSION_LOG_READ,
            ),
            NavigationContribution(
                label="Usage Rankings",
                url="/admin/ai-governance/relay-rankings",
                icon="trending-up",
                group="ai",
                order=50,
                permission=PERMISSION_LOG_READ,
            ),
            NavigationContribution(
                label="Relay Ledger",
                url="/admin/ai-governance/relay-ledger",
                icon="wallet",
                group="ai",
                order=60,
                permission=PERMISSION_LEDGER,
            ),
        ),
    ),
)

_HEALTH_DEFS: tuple[AdminHealthDefinition, ...] = (
    AdminHealthDefinition(
        name="governance.billing",
        contributor="ai-governance",
        component="Relay Billing",
        check_endpoint="/admin/ai-governance/health/billing",
        description="Aggregates billing store and reservation availability.",
    ),
)

_PAGE_DEFS: tuple[ManagementPageDefinition, ...] = (
    ManagementPageDefinition(
        name="governance_relay_usage",
        title="Relay Usage",
        contributor="ai-governance",
        route_path="/ai-governance/relay-usage",
        handler="lexigram.ai.governance.admin.pages:GovernanceRelayUsagePage",
        category=PageCategory.AI,
        icon="bar-chart",
        description="Settled relay usage, tokens, and spend",
        order=10,
    ),
    ManagementPageDefinition(
        name="governance_relay_quotas",
        title="Relay Quotas",
        contributor="ai-governance",
        route_path="/ai-governance/relay-quotas",
        handler="lexigram.ai.governance.admin.pages:GovernanceQuotasPage",
        category=PageCategory.AI,
        icon="gauge",
        description="Per-dimension admission capacity remaining",
        order=20,
    ),
    ManagementPageDefinition(
        name="governance_relay_settlements",
        title="Relay Settlements",
        contributor="ai-governance",
        route_path="/ai-governance/relay-settlements",
        handler="lexigram.ai.governance.admin.pages:GovernanceSettlementsPage",
        category=PageCategory.AI,
        icon="receipt",
        description="Failed settlements and conversion loss",
        order=30,
    ),
    ManagementPageDefinition(
        name="governance_relay_logs",
        title="Request Logs",
        contributor="ai-governance",
        route_path="/ai-governance/relay-logs",
        handler="lexigram.ai.governance.admin.logs_pages:RelayRequestLogsPage",
        category=PageCategory.AI,
        icon="list",
        permission=PERMISSION_LOG_READ,
        description="Redaction-safe dispatch metadata per request",
        order=40,
    ),
    ManagementPageDefinition(
        name="governance_relay_rankings",
        title="Usage Rankings",
        contributor="ai-governance",
        route_path="/ai-governance/relay-rankings",
        handler="lexigram.ai.governance.admin.logs_pages:RelayUsageRankingsPage",
        category=PageCategory.AI,
        icon="trending-up",
        permission=PERMISSION_LOG_READ,
        description="Per-model completion tokens and cost",
        order=50,
    ),
    ManagementPageDefinition(
        name="governance_relay_ledger",
        title="Relay Ledger",
        contributor="ai-governance",
        route_path="/ai-governance/relay-ledger",
        handler="lexigram.ai.governance.admin.ledger_pages:RelayLedgerPage",
        category=PageCategory.AI,
        icon="wallet",
        permission=PERMISSION_LEDGER,
        description="Ledger top-ups and daily check-ins",
        order=60,
    ),
)

_ACTIONS: tuple[AdminActionDefinition, ...] = (
    AdminActionDefinition(
        name="settle_topup",
        title="Settle Top-Up",
        contributor="ai-governance",
        handler="lexigram.ai.governance.admin.ledger_actions:settle_topup",
        icon="check-circle",
        confirmation_message="Settle this pending top-up as completed?",
        category="billing",
        permission=PERMISSION_LEDGER,
        parameter_schema=ActionParameterSchema(
            description=(
                "Flip a pending ledger top-up reference to completed "
                "when the backing payment settled."
            ),
            fields=(
                ActionParameterField(
                    name="reference_id",
                    type_hint="str",
                    required=True,
                    description="Ledger reference ID of the credit.",
                ),
                ActionParameterField(
                    name="expected_status",
                    type_hint="str",
                    required=False,
                    default="pending",
                    choices=("pending", "completed", "failed"),
                    description="Current status the reference must hold.",
                ),
            ),
        ),
    ),
    AdminActionDefinition(
        name="run_checkin",
        title="Run Daily Check-In",
        contributor="ai-governance",
        handler="lexigram.ai.governance.admin.ledger_actions:run_checkin",
        icon="calendar-check",
        confirmation_message="Record a daily check-in award for this user?",
        category="billing",
        permission=PERMISSION_LEDGER,
        parameter_schema=ActionParameterSchema(
            description=(
                "Credit one user a caller-supplied daily award.  Reward "
                "policy (amount, cadence) is decided by the application."
            ),
            fields=(
                ActionParameterField(
                    name="user_id",
                    type_hint="str",
                    required=True,
                    description="User receiving the award.",
                ),
                ActionParameterField(
                    name="award",
                    type_hint="str",
                    required=True,
                    description='Award amount, e.g. "5".',
                ),
            ),
        ),
    ),
)


class GovernanceAdminContributor(BaseAdminContributor):
    """Admin contributor for AI governance relay accounting.

    Provides current-spend, token-dimension, quota-pressure, and
    settlement-failure widgets plus management pages for relay usage,
    quotas, and settlements.  Registered via the
    ``lexigram.admin.contributors`` entry point.
    """

    name = "ai-governance"
    display_name = "AI Governance"
    group = "ai"
    icon = "shield"
    priority = 58

    required_permissions = frozenset({PERMISSION_READ, PERMISSION_LEDGER})

    def __init__(self) -> None:
        self._container: Any = None
        self._store: RelayUsageStoreProtocol | None = None
        self._manager: RelayReservationManager | None = None

    async def on_admin_boot(self, container: Any) -> None:
        """Resolve the billing store and reservation manager from DI.

        Args:
            container: The DI container resolver.
        """
        self._container = container
        try:
            self._store = await container.resolve(RelayUsageStoreProtocol)
        except Exception:
            self._store = None
        try:
            self._manager = await container.resolve(RelayReservationManager)
        except Exception:
            self._manager = None

    def get_dashboard_widgets(self) -> Sequence[DashboardWidgetDefinition]:
        return list(_WIDGETS)

    def get_navigation_items(self) -> Sequence[NavigationContribution]:
        return list(_NAV_ITEMS)

    def get_health_definitions(self) -> Sequence[AdminHealthDefinition]:
        return list(_HEALTH_DEFS)

    def get_routes(self) -> Sequence[AdminRouteSpec]:
        """Return the widget and health render endpoints.

        Returns:
            One route spec per dashboard widget and health check.
        """
        routes: list[AdminRouteSpec] = [
            AdminRouteSpec(
                path=cast("str", widget.render_endpoint),
                method="GET",
                handler=_render_placeholder,
                name=f"widgets.{widget.name}",
                permissions=frozenset({PERMISSION_READ}),
            )
            for widget in _WIDGETS
        ]
        routes += [
            AdminRouteSpec(
                path=cast("str", health.check_endpoint),
                method="GET",
                handler=_render_placeholder,
                name=f"health.{health.name}",
                permissions=frozenset({PERMISSION_READ}),
            )
            for health in _HEALTH_DEFS
        ]
        return routes

    def get_management_pages(self) -> Sequence[ManagementPageDefinition]:
        return list(_PAGE_DEFS)

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
        validation before invoking the ledger service.

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
            raise LookupError(f"unknown ai-governance action {action_name!r}")
        module_path, _, handler_name = definition.handler.partition(":")
        module = _import_module(module_path)
        handler = getattr(module, handler_name)
        if self._container is None:
            raise RuntimeError("contributor has no container; on_admin_boot required")
        return await handler(self._container, **params)

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
            "current_spend": self._render_current_spend,
            "token_dimensions": self._render_token_dimensions,
            "quota_pressure": self._render_quota_pressure,
            "settlement_failures": self._render_settlement_failures,
        }
        renderer = renderers.get(widget_name)
        if renderer is None:
            not_found: Result[WidgetViewModel, AdminError] = cast(
                "Result[WidgetViewModel, AdminError]",
                Err(WidgetNotFoundError("ai-governance", widget_name)),
            )
            return not_found
        html = await renderer(params)
        return Ok(WidgetViewModel(body=html))

    async def render_health_check(
        self,
        check_name: str,
    ) -> Result[HealthCheckPayload, AdminError]:
        """Render the aggregate billing health check.

        Args:
            check_name: Name of the health check; only
                ``governance.billing`` is served.

        Returns:
            Ok(HealthCheckPayload) with availability status; Err when the
            check is unknown.
        """
        if check_name != "governance.billing":
            not_found: Result[HealthCheckPayload, AdminError] = cast(
                "Result[HealthCheckPayload, AdminError]",
                Err(HealthCheckNotFoundError("ai-governance", check_name)),
            )
            return not_found
        if self._store is None or self._manager is None:
            return Ok(
                HealthCheckPayload(
                    status=HealthStatus.DEGRADED,
                    component="Relay Billing",
                    detail=(
                        "degraded (billing store or reservation manager "
                        "unavailable)"
                    ),
                )
            )
        return Ok(
            HealthCheckPayload(
                status=HealthStatus.HEALTHY,
                component="Relay Billing",
                detail="available",
            )
        )

    async def _reporter(self) -> RelayUsageReportService | None:
        """Return a report service over the resolved store, if any."""
        if self._store is None:
            return None
        return RelayUsageReportService(self._store)

    async def _render_current_spend(self, params: WidgetParams) -> str:
        """Render the settled charge for the widget window."""
        reporter = await self._reporter()
        if reporter is None:
            return render_to_string(
                _unavailable("Billing store unavailable; spend not measured.")
            )
        report = await self._report_window(reporter, params.time_window_minutes)
        return render_to_string(
            Card(
                title="Current Spend",
                content=render_to_string(
                    el(
                        "div",
                        el(
                            "p",
                            f"{report.totals.total_charge:.4f}",
                            class_="text-2xl font-bold text-[var(--foreground)]",
                        ),
                        el(
                            "p",
                            f"{report.total_rows} requests in the window",
                            class_="text-sm text-[var(--muted-foreground)] mt-1",
                        ),
                    )
                ),
            )
        )

    async def _render_token_dimensions(self, params: WidgetParams) -> str:
        """Render prompt/completion/total tokens for the window."""
        reporter = await self._reporter()
        if reporter is None:
            return render_to_string(
                _unavailable("Billing reporting unavailable; no token data.")
            )
        report = await self._report_window(reporter, params.time_window_minutes)
        totals = report.totals
        return render_to_string(
            Card(
                title="Token Dimensions",
                content=render_to_string(
                    el(
                        "div",
                        el(
                            "p",
                            f"Prompt {totals.prompt_tokens:,}",
                            class_="text-sm py-1",
                        ),
                        el(
                            "p",
                            f"Completion {totals.completion_tokens:,}",
                            class_="text-sm py-1",
                        ),
                        el(
                            "p",
                            f"Total {totals.total_tokens:,}",
                            class_="text-sm text-[var(--muted-foreground)] py-1",
                        ),
                    )
                ),
            )
        )

    async def _render_quota_pressure(self, params: WidgetParams) -> str:
        """Render remaining capacity per configured dimension."""
        del params
        if self._manager is None:
            return render_to_string(
                _unavailable("Quota reporting requires the reservation manager.")
            )
        snapshot = await self._manager.quota_snapshot()
        lines = []
        for entry in (
            snapshot.tenant,
            snapshot.account,
            snapshot.user,
            snapshot.model,
            snapshot.provider,
            snapshot.channel,
        ):
            if entry is None:
                continue
            lines.append(
                el(
                    "p",
                    (
                        f"{entry.dimension}: {entry.remaining_tokens():,} tokens · "
                        f"{entry.remaining_charge():.4f} charge"
                    ),
                    class_="text-sm py-1",
                )
            )
        if not lines:
            lines.append(
                el(
                    "p",
                    "No quota limits configured.",
                    class_="text-sm text-[var(--muted-foreground)] py-1",
                )
            )
        return render_to_string(
            Card(title="Quota Pressure", content=render_to_string(el("div", *lines)))
        )

    async def _render_settlement_failures(self, params: WidgetParams) -> str:
        """Render failed settlement counts in the widget window."""
        reporter = await self._reporter()
        if reporter is None:
            return render_to_string(
                _unavailable("Billing reporting unavailable; no failure data.")
            )
        report = await self._report_window(
            reporter, params.time_window_minutes, status="failed"
        )
        failed = sum(report.totals.status_counts.values())
        return render_to_string(
            Card(
                title="Settlement Failures",
                content=render_to_string(
                    el(
                        "div",
                        el(
                            "p",
                            str(failed),
                            class_="text-2xl font-bold text-[var(--foreground)]",
                        ),
                        el(
                            "p",
                            (
                                f"{report.totals.total_charge:.4f} charge on failed "
                                "settlements"
                            ),
                            class_="text-sm text-[var(--muted-foreground)] mt-1",
                        ),
                    )
                ),
            )
        )

    async def _report_window(
        self,
        reporter: RelayUsageReportService,
        minutes: int,
        *,
        status: str | None = None,
    ) -> RelayUsageReport:
        """Run a windowed report for widget data.

        Args:
            reporter: The report service to query.
            minutes: Widget window length in minutes.
            status: Optional terminal status filter.

        Returns:
            The bounded usage report for the window.
        """
        end = clock.now()
        start = end - timedelta(minutes=minutes)
        return await reporter.report(
            start=start,
            end=end,
            page=1,
            page_size=1,
            status=status,
        )


async def _render_placeholder(request: object) -> str:  # noqa: ARG001
    """Placeholder route handler for widget endpoints.

    Widget content is rendered by the admin dashboard through
    ``render_widget``; the route spec only proves registration.
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
