"""Static contribution definitions for the AI governance admin surface.

Dashboard widget definitions, navigation items, health checks,
management pages, and admin actions surfaced by
:class:`~lexigram.ai.governance.admin.contributor.GovernanceAdminContributor`.
"""

from __future__ import annotations

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
    WidgetSize,
)

__all__ = [
    "PERMISSION_LEDGER",
    "PERMISSION_LOG_READ",
    "PERMISSION_READ",
]

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
