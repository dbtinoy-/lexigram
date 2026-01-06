from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from lexigram.contracts.admin.contributor import BaseAdminContributor
from lexigram.contracts.admin.types import (
    ManagementPageDefinition,
    NavigationContribution,
    PageCategory,
)

if TYPE_CHECKING:
    from lexigram.contracts.core.di import ContainerResolverProtocol

_NAV_ITEMS: tuple[NavigationContribution, ...] = (
    NavigationContribution(
        label="Moderation",
        url="/admin/ai/moderation",
        icon="shield",
        group="ai",
        order=60,
    ),
)


class GuardAdminContributor(BaseAdminContributor):
    """Admin contributor for the guard pipeline (Moderation)."""

    name = "ai-guard"
    display_name = "Moderation"
    group = "ai"
    icon = "shield"
    priority = 60

    def __init__(self) -> None:
        self._container: ContainerResolverProtocol | None = None

    async def on_admin_boot(self, container: ContainerResolverProtocol) -> None:
        self._container = container

    def get_navigation_items(self) -> Sequence[NavigationContribution]:
        return list(_NAV_ITEMS)

    def get_management_pages(self) -> Sequence[ManagementPageDefinition]:
        return [
            ManagementPageDefinition(
                name="moderation_overview",
                title="Moderation",
                contributor="ai-guard",
                route_path="/ai/moderation",
                handler="lexigram.ai.guard.admin.pages.overview:ModerationOverviewPage",
                category=PageCategory.AI,
                icon="shield",
                description="Content safety guard pipeline status and configuration",
                order=10,
            ),
        ]


__all__ = ["GuardAdminContributor"]
