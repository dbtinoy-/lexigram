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
from importlib import import_module
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
    WidgetKind,
    WidgetParams,
    WidgetSize,
    WidgetViewModel,
)
from lexigram.contracts.admin.widget_content import (
    MessageContent,
    Stat,
    StatContent,
    WidgetContent,
)
from lexigram.contracts.ai.governance import RelayUsageStoreProtocol
from lexigram.contracts.core.health import HealthStatus
from lexigram.contracts.exceptions.container import ContainerError
from lexigram.logging import get_logger
from lexigram.primitives import clock
from lexigram.result import Err, Ok, Result

if TYPE_CHECKING:
    from lexigram.contracts.admin.errors import AdminError

__all__ = ["GovernanceAdminContributor"]

PERMISSION_READ = "governance.read"
PERMISSION_LOG_READ = "relay.logs"
PERMISSION_LEDGER = "relay.billing"

logger = get_logger(__name__)

_WIDGETS: tuple[DashboardWidgetDefinition, ...] = (
    DashboardWidgetDefinition(
        name="current_spend",
        title="Current Spend",
        contributor="ai-governance",
        render_endpoint="/admin/ai-governance/widgets/current_spend",
        size=WidgetSize.MEDIUM,
        category=WidgetCategory.RESOURCES,
        view_kind=WidgetKind.STAT,
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
        view_kind=WidgetKind.STAT,
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
        view_kind=WidgetKind.STAT,
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
        view_kind=WidgetKind.STAT,
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

    required_permissions = frozenset(
        {PERMISSION_READ, PERMISSION_LOG_READ, PERMISSION_LEDGER}
    )

    def __init__(self) -> None:
        self._container: Any = None
        self._store: RelayUsageStoreProtocol | None = None
        self._manager: RelayReservationManager | None = None
        self._action_handlers: dict[str, Any] = {}

    async def on_admin_boot(self, container: Any) -> None:
        """Resolve the billing store and reservation manager from DI.

        Widgets that depend on a missing service render an explicit
        unavailable ``MessageContent`` state rather than failing
        the whole admin boot — but the resolution failure itself is
        always logged so it isn't silently invisible in production.

        Args:
            container: The DI container resolver.
        """
        self._container = container
        try:
            self._store = await container.resolve(RelayUsageStoreProtocol)
        except ContainerError:
            logger.warning(
                "governance.dependency_unavailable",
                dependency="RelayUsageStoreProtocol",
            )
            self._store = None
        try:
            self._manager = await container.resolve(RelayReservationManager)
        except ContainerError:
            logger.warning(
                "governance.dependency_unavailable",
                dependency="RelayReservationManager",
            )
            self._manager = None
        self._action_handlers = {}
        for action in _ACTIONS:
            module_path, _, handler_name = action.handler.partition(":")
            module = import_module(module_path)
            self._action_handlers[action.name] = getattr(module, handler_name)

    def get_dashboard_widgets(self) -> Sequence[DashboardWidgetDefinition]:
        return list(_WIDGETS)

    def get_navigation_items(self) -> Sequence[NavigationContribution]:
        return list(_NAV_ITEMS)

    def get_health_definitions(self) -> Sequence[AdminHealthDefinition]:
        return list(_HEALTH_DEFS)

    def get_management_pages(self) -> Sequence[ManagementPageDefinition]:
        return list(_PAGE_DEFS)

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
        handler = self._action_handlers.get(action_name)
        if handler is None:
            raise LookupError(f"unknown ai-governance action {action_name!r}")
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
            Ok(WidgetViewModel) with structured content on success;
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
        content = await renderer(params)
        return Ok(WidgetViewModel(content=content))

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
                    component="AI Governance Billing",
                    detail=(
                        "degraded (billing store or reservation manager unavailable)"
                    ),
                )
            )
        return Ok(
            HealthCheckPayload(
                status=HealthStatus.HEALTHY,
                component="AI Governance Billing",
                detail="available",
            )
        )

    async def _reporter(self) -> RelayUsageReportService | None:
        """Return a report service over the resolved store, if any."""
        if self._store is None:
            return None
        return RelayUsageReportService(self._store)

    async def _render_current_spend(self, params: WidgetParams) -> WidgetContent:
        """Render the settled charge for the widget window."""
        reporter = await self._reporter()
        if reporter is None:
            return MessageContent(text="Billing store unavailable; spend not measured.")
        report = await self._report_window(reporter, params.time_window_minutes)
        return StatContent(
            stats=(
                Stat(label="Current Spend", value=f"{report.totals.total_charge:.4f}"),
                Stat(
                    label="Request Volume",
                    value=f"{report.total_rows} requests in the window",
                ),
            )
        )

    async def _render_token_dimensions(self, params: WidgetParams) -> WidgetContent:
        """Render prompt/completion/total tokens for the window."""
        reporter = await self._reporter()
        if reporter is None:
            return MessageContent(text="Billing reporting unavailable; no token data.")
        report = await self._report_window(reporter, params.time_window_minutes)
        totals = report.totals
        return StatContent(
            stats=(
                Stat(label="Prompt Tokens", value=f"{totals.prompt_tokens:,}"),
                Stat(label="Completion Tokens", value=f"{totals.completion_tokens:,}"),
                Stat(label="Total Tokens", value=f"{totals.total_tokens:,}"),
            )
        )

    async def _render_quota_pressure(self, params: WidgetParams) -> WidgetContent:
        """Render remaining capacity per configured dimension."""
        del params
        if self._manager is None:
            return MessageContent(
                text="Quota reporting unavailable; reservation manager missing."
            )
        snapshot = await self._manager.quota_snapshot()
        stats: list[Stat] = []
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
            stats.append(
                Stat(
                    label=f"{entry.dimension}",
                    value=(
                        f"{entry.remaining_tokens():,} tokens · "
                        f"{entry.remaining_charge():.4f} charge"
                    ),
                )
            )
        if not stats:
            return MessageContent(text="No quota limits configured.")
        return StatContent(stats=tuple(stats))

    async def _render_settlement_failures(self, params: WidgetParams) -> WidgetContent:
        """Render failed settlement counts in the widget window."""
        reporter = await self._reporter()
        if reporter is None:
            return MessageContent(
                text="Billing reporting unavailable; no failure data."
            )
        report = await self._report_window(
            reporter, params.time_window_minutes, status="failed"
        )
        failed = sum(report.totals.status_counts.values())
        return StatContent(
            stats=(
                Stat(label="Failed Settlements", value=str(failed)),
                Stat(
                    label="Failed Charge",
                    value=f"{report.totals.total_charge:.4f} charge on failed settlements",
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
