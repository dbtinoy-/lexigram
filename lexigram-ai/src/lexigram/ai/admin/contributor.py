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
        label="AI Pipeline",
        url="/admin/ai/pipeline",
        icon="activity",
        group="ai",
        order=55,
    ),
)


class AIPipelineAdminContributor(BaseAdminContributor):
    """Admin contributor for the AI pipeline overview."""

    name = "ai-pipeline"
    display_name = "AI Pipeline"
    group = "ai"
    icon = "activity"
    priority = 55

    def __init__(self) -> None:
        self._container: ContainerResolverProtocol | None = None

    async def on_admin_boot(self, container: ContainerResolverProtocol) -> None:
        self._container = container

    def get_navigation_items(self) -> Sequence[NavigationContribution]:
        return list(_NAV_ITEMS)

    def get_management_pages(self) -> Sequence[ManagementPageDefinition]:
        return [
            ManagementPageDefinition(
                name="ai_pipeline_overview",
                title="AI Pipeline",
                contributor="ai-pipeline",
                route_path="/ai/pipeline",
                handler="lexigram.ai.admin.pages.overview:AIPipelineOverviewPage",
                category=PageCategory.AI,
                icon="activity",
                description="AI pipeline overview, subsystem status, and configuration",
                order=10,
            ),
        ]


__all__ = ["AIPipelineAdminContributor"]
