"""Infrastructure center controller — built-in cluster landing page.

Shows an overview of the areas contributed to the ``infrastructure``
navigation group (web, sql, cache, events, queue, tasks) as linked cards.
The secondary nav column renders inside the content section next to the
overview (settings ConfigLayout pattern).

This is the concrete instance of the generic
:class:`~lexigram.admin.controllers.clusters.ClusterCenterController`
bound to the built-in infrastructure cluster.
"""

from __future__ import annotations

from typing import Any

from lexigram.admin.clusters.registry import INFRASTRUCTURE_CLUSTER
from lexigram.admin.controllers.clusters import ClusterCenterController
from lexigram.admin.engine.renderer import AdminRenderer

__all__ = ["InfrastructureController"]


class InfrastructureController(ClusterCenterController):
    """Landing page for the Infrastructure center.

    Routes:
        GET /admin/infrastructure  - Overview of cluster areas
    """

    prefix = "/infrastructure"

    def __init__(
        self,
        renderer: AdminRenderer,
        settings_service: Any | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            renderer=renderer,
            cluster=INFRASTRUCTURE_CLUSTER,
            settings_service=settings_service,
            **kwargs,
        )
