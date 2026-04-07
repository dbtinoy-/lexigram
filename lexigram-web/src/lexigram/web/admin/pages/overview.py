from __future__ import annotations

from typing import Any

from starlette.responses import HTMLResponse

from lexigram.logging import get_logger
from lexigram.ui import Card, Divider, Grid, StatCard, el, render_to_string
from lexigram.web.routing.controller_registry import ControllerRegistry
from lexigram.web.routing.registry import RouteRegistry

logger = get_logger(__name__)


class WebOverviewPage:
    """Dashboard overview for /admin/web."""

    def __init__(
        self,
        route_registry: RouteRegistry | None = None,
        controller_registry: ControllerRegistry | None = None,
    ) -> None:
        self._route_registry = route_registry
        self._controller_registry = controller_registry

    async def handle(self, request: Any) -> HTMLResponse:
        total_routes = 0
        total_controllers = 0

        try:
            if self._route_registry is not None:
                routes = self._route_registry.get_all_routes()
                total_routes = sum(len(methods) for methods in routes.values())
        except Exception as exc:
            logger.warning("web_overview.routes_unavailable", error=str(exc))

        try:
            if self._controller_registry is not None:
                total_controllers = len(self._controller_registry.get_all_controllers())
        except Exception as exc:
            logger.warning("web_overview.controllers_unavailable", error=str(exc))

        html = render_to_string(
            el(
                "div",
                el("h1", "Web", class_="text-2xl font-bold text-[var(--foreground)]"),
                el(
                    "p",
                    "HTTP routing and controller management.",
                    class_="text-sm text-[var(--muted-foreground)] mt-1 mb-6",
                ),
                Divider(),
                Grid(
                    StatCard(
                        label="Total Routes",
                        value=str(total_routes),
                        icon="map",
                    ),
                    StatCard(
                        label="Total Controllers",
                        value=str(total_controllers),
                        icon="layers",
                    ),
                    cols={"default": 1, "lg": 2},
                    gap=4,
                    class_="mb-6 mt-6",
                ),
                Card(
                    title="Web Details",
                    content=render_to_string(
                        el(
                            "dl",
                            el(
                                "dt",
                                "Total Routes",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                str(total_routes),
                                class_="text-sm text-[var(--foreground)] pb-3",
                            ),
                            el(
                                "dt",
                                "Total Controllers",
                                class_="text-sm font-semibold text-[var(--muted-foreground)] py-2",
                            ),
                            el(
                                "dd",
                                str(total_controllers),
                                class_="text-sm text-[var(--foreground)] pb-3",
                            ),
                            class_="divide-y divide-[var(--border)]",
                        ),
                    ),
                ),
                class_="p-6",
            ),
        )
        return HTMLResponse(html)
