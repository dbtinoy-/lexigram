from __future__ import annotations

from collections.abc import Sequence

from lexigram.admin.dashboard.naming_policy import NamingPolicy
from lexigram.admin.dashboard.permission_filter import PermissionFilter
from lexigram.admin.types import AdminUser
from lexigram.contracts.admin import (
    BaseAdminContributor,
    SettingsPanelDefinition,
)


class SettingsPanelAssembler:
    """Collects and validates ``SettingsPanelDefinition`` from contributors."""

    def __init__(
        self,
        *,
        naming_policy: NamingPolicy,
        permission_filter: PermissionFilter,
    ) -> None:
        self._naming = naming_policy
        self._perms = permission_filter

    def assemble(
        self,
        contributors: Sequence[BaseAdminContributor],
        user: AdminUser | None = None,
    ) -> list[SettingsPanelDefinition]:
        """Collect settings panels from all *contributors*."""
        collected: list[SettingsPanelDefinition] = []
        for c in contributors:
            for panel in c.get_settings_panels():
                ns_name = self._naming.namespaced(c.package_source, panel.name)
                self._naming.register("settings", ns_name)
                p = SettingsPanelDefinition(
                    name=ns_name,
                    title=panel.title,
                    contributor=c.package_source,
                    route_path=panel.route_path,
                    handler=panel.handler,
                    icon=panel.icon,
                    category=panel.category,
                    permission=panel.permission,
                )
                collected.append(p)
        return self._perms.filter(
            collected,
            user,
            get_required_permissions=lambda p: (
                frozenset({p.permission}) if p.permission else frozenset()
            ),
        )
