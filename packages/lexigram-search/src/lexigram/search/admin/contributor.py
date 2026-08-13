"""Admin contributor for lexigram-search.

Registers the ``lexigram.admin.contributors`` entry point for lexigram-search
and surfaces the global search page (``/admin/search``, served by
lexigram-admin) in the admin navigation.  Depends only on
``lexigram-contracts`` + ``lexigram``.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from lexigram.contracts.admin.contributor import BaseAdminContributor
from lexigram.contracts.admin.types import (
    AdminActionDefinition,
    AdminHealthDefinition,
    DashboardWidgetDefinition,
    ManagementPageDefinition,
    NavigationContribution,
)

if TYPE_CHECKING:
    from lexigram.contracts.core.di import ContainerResolverProtocol

_NAV_ITEMS: tuple[NavigationContribution, ...] = (
    NavigationContribution(
        label="Search",
        url="/admin/search",
        icon="search",
        group="search",
        order=0,
    ),
)


class SearchAdminContributor(BaseAdminContributor):
    """Admin contributor for the lexigram-search package.

    Attributes:
        name: Contributor identifier used in entry-point registration.
        display_name: Human-facing contributor name.
    """

    name = "search"
    display_name = "Search"
    group = "search"
    icon = "search"
    priority = 60

    async def on_admin_boot(self, container: ContainerResolverProtocol) -> None:
        """Resolve DI dependencies from the container at admin boot.

        Args:
            container: The DI container resolver.
        """

    def get_dashboard_widgets(self) -> Sequence[DashboardWidgetDefinition]:
        """Return dashboard widgets contributed by this package.

        Returns:
            An empty sequence until the query-builder/global-search widgets
            land in the 05 workstream.
        """
        return []

    def get_navigation_items(self) -> Sequence[NavigationContribution]:
        """Return navigation contributions.

        Returns:
            A single ``Search`` item pointing at the admin global search
            page (``/admin/search``, served by lexigram-admin).
        """
        return list(_NAV_ITEMS)

    def get_health_definitions(self) -> Sequence[AdminHealthDefinition]:
        """Return admin health definitions.

        Returns:
            An empty sequence for the skeleton contributor.
        """
        return []

    def get_actions(self) -> Sequence[AdminActionDefinition]:
        """Return admin action definitions.

        Returns:
            An empty sequence for the skeleton contributor.
        """
        return []

    def get_management_pages(self) -> Sequence[ManagementPageDefinition]:
        """Return management pages.

        Returns:
            An empty sequence: the global search page is served by
            lexigram-admin core at ``/admin/search`` (wired in via the
            navigation contribution above) rather than duplicated here.
        """
        return []


__all__ = ["SearchAdminContributor"]
