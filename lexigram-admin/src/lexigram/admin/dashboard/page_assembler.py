from __future__ import annotations

from collections.abc import Sequence

from lexigram.admin.dashboard.naming_policy import NamingPolicy
from lexigram.admin.dashboard.permission_filter import PermissionFilter
from lexigram.admin.types import AdminUser
from lexigram.contracts.admin import (
    BaseAdminContributor,
    ManagementPageDefinition,
)


class PageAssembler:
    """Collects and validates ``ManagementPageDefinition`` from contributors."""

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
    ) -> list[ManagementPageDefinition]:
        """Collect pages from all *contributors*, namespacing and filtering."""
        collected: list[ManagementPageDefinition] = []
        for c in contributors:
            for page in c.get_management_pages():
                ns_name = self._naming.namespaced(c.package_source, page.name)
                self._naming.register("page", ns_name)
                p = ManagementPageDefinition(
                    name=ns_name,
                    title=page.title,
                    contributor=c.package_source,
                    route_path=page.route_path,
                    handler=page.handler,
                    category=page.category,
                    permission=page.permission,
                )
                collected.append(p)
        return self._perms.filter(
            collected,
            user,
            get_required_permissions=lambda p: (
                frozenset({p.permission}) if p.permission else frozenset()
            ),
        )
