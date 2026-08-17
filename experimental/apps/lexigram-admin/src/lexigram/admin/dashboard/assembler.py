"""Dashboard assembler — implements AdminDashboardProtocol."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from lexigram.admin.contributors.exceptions import (
    ContributorNotFoundError,
    ContributorPermissionError,
)
from lexigram.admin.dashboard.permission_filter import PermissionFilter
from lexigram.contracts.admin.protocols import AdminContributorProtocol
from lexigram.contracts.admin.types import (
    AdminActionDefinition,
    DashboardWidgetDefinition,
    ManagementPageDefinition,
    NavigationContribution,
    SettingsPanelDefinition,
)
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.admin.dashboard.page_assembler import PageAssembler
    from lexigram.admin.dashboard.settings_assembler import SettingsPanelAssembler
    from lexigram.admin.types import AdminUser

logger = get_logger(__name__)


class DashboardAssembler:
    """Assembles the admin dashboard from contributor definitions.

    Collects widgets, navigation, health definitions, pages, settings
    panels, and actions from all registered contributors and presents a
    unified view.  Enforces RBAC on ``execute_action`` via each
    contributor's ``required_permissions`` attribute.

    Args:
        contributors: Ordered sequence of contributors to assemble.
        page_assembler: Optional PageAssembler for management pages.
        settings_assembler: Optional SettingsPanelAssembler for settings.
    """

    def __init__(
        self,
        contributors: Sequence[AdminContributorProtocol],
        *,
        page_assembler: PageAssembler | None = None,
        settings_assembler: SettingsPanelAssembler | None = None,
        permission_filter: PermissionFilter | None = None,
    ) -> None:
        self._contributors: Sequence[AdminContributorProtocol] = contributors
        self._contributors_by_id: dict[str, AdminContributorProtocol] = {
            c.contributor_id: c for c in contributors
        }
        self._page_assembler = page_assembler
        self._settings_assembler = settings_assembler
        self._perms = permission_filter or PermissionFilter()

    async def get_all_widgets(
        self, user: AdminUser | None = None
    ) -> Sequence[DashboardWidgetDefinition]:
        """Collect, dedupe, permission-filter, and sort widgets from all contributors.

        When two contributors register a widget with the same ``name``, a
        ``admin_widget_conflict`` warning is emitted and the later contributor's
        widget replaces the earlier one (last writer wins).
        """
        seen: dict[str, str] = {}  # name → contributor_id of last writer
        by_name: dict[str, DashboardWidgetDefinition] = {}
        for contributor in self._contributors:
            for widget in contributor.get_dashboard_widgets():
                if widget.name in seen:
                    logger.warning(
                        "admin_widget_conflict",
                        widget_name=widget.name,
                        first_contributor=seen[widget.name],
                        second_contributor=contributor.contributor_id,
                    )
                seen[widget.name] = contributor.contributor_id
                by_name[widget.name] = widget
        sorted_widgets = sorted(
            by_name.values(), key=lambda w: (w.category.value, w.order)
        )
        return self._perms.filter(
            sorted_widgets,
            user,
            get_required_permissions=lambda w: (
                frozenset({w.permission}) if w.permission else frozenset()
            ),
        )

    async def get_all_navigation(self) -> Sequence[NavigationContribution]:
        """Collect and sort navigation from all contributors by group then order.

        When two contributors register a navigation item with the same ``label``,
        an ``admin_navigation_conflict`` warning is emitted and the later
        contributor's item replaces the earlier one (last writer wins).
        """
        seen: dict[str, str] = {}  # label → contributor_id of last writer
        by_label: dict[str, NavigationContribution] = {}
        for contributor in self._contributors:
            for item in contributor.get_navigation_items():
                if item.label in seen:
                    logger.warning(
                        "admin_navigation_conflict",
                        item_label=item.label,
                        first_contributor=seen[item.label],
                        second_contributor=contributor.contributor_id,
                    )
                seen[item.label] = contributor.contributor_id
                by_label[item.label] = item
        return sorted(by_label.values(), key=lambda n: (n.group, n.order))

    async def get_framework_health(self) -> dict[str, HealthCheckResult]:
        """Collect health definitions from all contributors.

        Returns a dict mapping health definition name to a placeholder
        HealthCheckResult.  Actual checks are performed lazily via
        the ``check_endpoint`` HTMX calls.
        """
        results: dict[str, HealthCheckResult] = {}
        for contributor in self._contributors:
            for health_def in contributor.get_health_definitions():
                results[health_def.name] = HealthCheckResult(
                    component=health_def.component,
                    status=HealthStatus.UNKNOWN,
                    message="Pending health check",
                )
        return results

    async def get_all_actions(self) -> Sequence[AdminActionDefinition]:
        """Collect actions from all contributors."""
        actions: list[AdminActionDefinition] = []
        for contributor in self._contributors:
            actions.extend(contributor.get_actions())
        return actions

    async def get_management_pages(
        self,
        user: AdminUser | None = None,
    ) -> list[ManagementPageDefinition]:
        """Collect management pages via PageAssembler or return empty."""
        if self._page_assembler is not None:
            return self._page_assembler.assemble(self._contributors, user=user)  # type: ignore[arg-type]
        return []

    async def get_settings_panels(
        self,
        user: AdminUser | None = None,
    ) -> list[SettingsPanelDefinition]:
        """Collect settings panels via SettingsPanelAssembler or return empty."""
        if self._settings_assembler is not None:
            return self._settings_assembler.assemble(self._contributors, user=user)  # type: ignore[arg-type]
        return []

    async def execute_action(
        self,
        contributor_id: str,
        action_name: str,
        params: dict[str, object],
        user_permissions: frozenset[str],
    ) -> object:
        """Execute a framework-level action after RBAC enforcement.

        Looks up the contributor by *contributor_id*, verifies that
        *user_permissions* is a superset of the contributor's
        ``required_permissions``, then delegates to
        ``contributor.execute_action(action_name, params)``.

        Args:
            contributor_id: Identifier of the target contributor.
            action_name: Name of the action to execute.
            params: Parameters forwarded to the action handler.
            user_permissions: Permissions held by the requesting user.

        Returns:
            Whatever the contributor's action handler returns.

        Raises:
            ContributorNotFoundError: If no contributor matches *contributor_id*.
            ContributorPermissionError: If *user_permissions* is missing any
                permissions declared by the contributor.
        """
        contributor = self._contributors_by_id.get(contributor_id)
        if contributor is None:
            raise ContributorNotFoundError(contributor_id)

        missing = contributor.required_permissions - user_permissions
        if missing:
            raise ContributorPermissionError(contributor_id, action_name, missing)

        return await contributor.execute_action(action_name, params)  # type: ignore[attr-defined]


__all__ = ["DashboardAssembler"]
