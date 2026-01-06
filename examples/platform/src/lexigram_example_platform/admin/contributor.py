"""Platform admin contributor.

Surfaces platform-specific widgets, navigation items, management pages,
and actions into the Lexigram admin dashboard via the contributor protocol.

The contributor is registered by :class:`~lexigram_example_platform.di.provider.PlatformProvider`
during the ``boot`` phase and is discovered by the admin shell at runtime.
"""

from __future__ import annotations

from collections.abc import Sequence

from lexigram.admin.contributors.base import BaseAdminContributor
from lexigram.contracts.admin.types import (
    AdminActionDefinition,
    AdminHealthDefinition,
    DashboardWidgetDefinition,
    ManagementPageDefinition,
    NavigationContribution,
    PageCategory,
    WidgetCategory,
    WidgetSize,
)

# ---------------------------------------------------------------------------
# Static definitions — declared at module level so they are created once.
# ---------------------------------------------------------------------------

_WIDGETS: tuple[DashboardWidgetDefinition, ...] = (
    DashboardWidgetDefinition(
        name="platform_tenant_count",
        title="Active Tenants",
        contributor="platform",
        render_endpoint="/admin/platform/widgets/tenant_count",
        size=WidgetSize.SMALL,
        category=WidgetCategory.METRICS,
        refresh_interval_seconds=60,
        order=10,
        icon="building-2",
        description="Number of active tenants currently provisioned.",
    ),
    DashboardWidgetDefinition(
        name="platform_membership_count",
        title="Total Memberships",
        contributor="platform",
        render_endpoint="/admin/platform/widgets/membership_count",
        size=WidgetSize.SMALL,
        category=WidgetCategory.METRICS,
        refresh_interval_seconds=60,
        order=20,
        icon="users",
        description="Total number of user–tenant membership records.",
    ),
    DashboardWidgetDefinition(
        name="platform_suspended_tenants",
        title="Suspended Tenants",
        contributor="platform",
        render_endpoint="/admin/platform/widgets/suspended_tenants",
        size=WidgetSize.MEDIUM,
        category=WidgetCategory.HEALTH,
        refresh_interval_seconds=120,
        order=30,
        icon="alert-circle",
        description="Tenants that are currently suspended.",
    ),
)

_NAV_ITEMS: tuple[NavigationContribution, ...] = (
    NavigationContribution(
        label="Platform",
        url="/admin/platform",
        icon="building-2",
        group="application",
        order=10,
        children=(
            NavigationContribution(
                label="Tenants",
                url="/admin/platform/tenants",
                icon="building",
                group="application",
                order=10,
            ),
            NavigationContribution(
                label="Memberships",
                url="/admin/platform/memberships",
                icon="users",
                group="application",
                order=20,
            ),
            NavigationContribution(
                label="Feature Flags",
                url="/admin/platform/features",
                icon="flag",
                group="application",
                order=30,
            ),
        ),
    ),
)

_MANAGEMENT_PAGES: tuple[ManagementPageDefinition, ...] = (
    ManagementPageDefinition(
        name="platform_tenants",
        title="Tenant Management",
        contributor="platform",
        route_path="/admin/platform/tenants",
        handler="lexigram_example_platform.admin.pages:tenants_page",
        category=PageCategory.CONFIGURATION,
        icon="building",
        description="View and manage all provisioned tenants.",
        order=10,
    ),
    ManagementPageDefinition(
        name="platform_memberships",
        title="Membership Management",
        contributor="platform",
        route_path="/admin/platform/memberships",
        handler="lexigram_example_platform.admin.pages:memberships_page",
        category=PageCategory.SECURITY,
        icon="users",
        description="Inspect and manage user–tenant memberships and roles.",
        order=20,
    ),
)

_HEALTH_DEFS: tuple[AdminHealthDefinition, ...] = (
    AdminHealthDefinition(
        name="platform.tenant_repo",
        contributor="platform",
        component="Tenant Repository",
        check_endpoint="/admin/platform/health/tenant_repo",
        icon="database",
        description="Verifies the tenant repository is operational.",
    ),
)

_ACTIONS: tuple[AdminActionDefinition, ...] = (
    AdminActionDefinition(
        name="suspend_tenant",
        title="Suspend Tenant",
        contributor="platform",
        handler="lexigram_example_platform.admin.actions:suspend_tenant",
        icon="pause-circle",
        confirmation_message="This will prevent the tenant's users from logging in. Continue?",
        permission="platform:tenants:suspend",
        destructive=True,
        category="tenant_operations",
    ),
)


class PlatformAdminContributor(BaseAdminContributor):
    """Admin contributor for the multi-tenant platform example.

    Surfaces tenant metrics, management pages, and operational actions
    into the Lexigram admin dashboard.

    Attributes:
        name: Stable contributor identifier used for RBAC lookup.
        display_name: Human-readable label shown in the dashboard.
        group: Navigation group this contributor belongs to.
        icon: Lucide icon name for the contributor's nav entry.
        priority: Render priority (lower renders earlier).
        version: Contributor schema version.
    """

    name = "platform"
    display_name = "Platform"
    group = "application"
    icon = "building-2"
    priority = 50
    version = "0.1.0"
    package_source = "lexigram-example-platform"
    required_permissions: frozenset[str] = frozenset(["platform:view"])

    def get_dashboard_widgets(self) -> Sequence[DashboardWidgetDefinition]:
        """Return platform dashboard widgets.

        Returns:
            Tenant count, membership count, and suspended-tenant widgets.
        """
        return list(_WIDGETS)

    def get_navigation_items(self) -> Sequence[NavigationContribution]:
        """Return platform navigation items.

        Returns:
            Top-level "Platform" entry with tenants, memberships, and feature
            flags children.
        """
        return list(_NAV_ITEMS)

    def get_management_pages(self) -> Sequence[ManagementPageDefinition]:
        """Return management page definitions.

        Returns:
            Tenant and membership management pages.
        """
        return list(_MANAGEMENT_PAGES)

    def get_health_definitions(self) -> Sequence[AdminHealthDefinition]:
        """Return health check definitions.

        Returns:
            Repository health check definition.
        """
        return list(_HEALTH_DEFS)

    def get_actions(self) -> Sequence[AdminActionDefinition]:
        """Return platform admin actions.

        Returns:
            Suspend-tenant destructive action.
        """
        return list(_ACTIONS)


__all__ = ["PlatformAdminContributor"]
