"""Infrastructure center controller — cluster landing page.

Shows an overview of the areas contributed to the ``infrastructure``
navigation group (web, sql, cache, events, queue, tasks) as linked cards.
The secondary nav column renders inside the content section next to the
overview (settings ConfigLayout pattern).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from starlette.requests import Request
from starlette.responses import Response

from lexigram.admin.controllers.base import AdminController
from lexigram.contracts.web import get
from lexigram.logging import get_logger
from lexigram.ui import el

if TYPE_CHECKING:
    from lexigram.admin.engine.renderer import AdminRenderer

logger = get_logger(__name__)

__all__ = ["InfrastructureController"]

_AREA_DESCRIPTIONS: dict[str, str] = {
    "web": "HTTP routing, middleware, and web API endpoints.",
    "sql": "Database connections, queries, and schema management.",
    "cache": "Cache backends, keys, and TTL policies.",
    "events": "Event bus, subscriptions, and message delivery.",
    "queue": "Background job queue and worker management.",
    "tasks": "Scheduled tasks, cron jobs, and automation.",
}

_DEFAULT_AREA_DESCRIPTION = "Manage and monitor this infrastructure area."


class InfrastructureController(AdminController):
    """Landing page for the Infrastructure center.

    Routes:
        GET /admin/infrastructure  - Overview of cluster areas
    """

    prefix = "/infrastructure"

    def __init__(self, renderer: AdminRenderer, **kwargs: Any) -> None:
        super().__init__(renderer=renderer, **kwargs)

    @get("/")
    async def index(self, request: Request) -> Response:
        from lexigram.admin.engine.renderer import resolve_admin_nav
        from lexigram.admin.navigation.clusters import cluster_items
        from lexigram.admin.ui.organisms.secondary_nav import ClusterLayout

        state = getattr(request, "app", None)
        groups = (
            getattr(state.state, "assembler_groups", None)
            if state and hasattr(state, "state")
            else None
        )
        content = self._render_overview(cluster_items(groups))
        _, _, secondary_nav = resolve_admin_nav(request)
        if secondary_nav:
            content = ClusterLayout(items=secondary_nav, content=content).render()
        return await self.render_admin(request, content, title="Infrastructure")

    def _render_overview(self, items: list[Any]) -> Any:
        header = el(
            "div",
            el(
                "h1",
                "Infrastructure",
                class_="text-2xl font-bold text-foreground",
            ),
            el(
                "p",
                "Monitor and manage the services powering your application: web, data, and runtime areas.",
                class_="text-muted-foreground mt-1",
            ),
            class_="mb-2",
        )

        if not items:
            return el(
                "div",
                header,
                el(
                    "div",
                    el("div", "⚙️", class_="text-5xl mb-4"),
                    el(
                        "h3",
                        "No Infrastructure Areas",
                        class_="text-lg font-semibold text-foreground",
                    ),
                    el(
                        "p",
                        "Install framework packages (web, sql, cache, events, queue, tasks) to populate this center.",
                        class_="text-muted-foreground mt-2 max-w-sm",
                    ),
                    class_="text-center py-16",
                ),
                class_="space-y-6",
            )

        cards = [self._render_card(item) for item in items]
        return el(
            "div",
            header,
            el(
                "div",
                *cards,
                class_="grid grid-cols-1 md:grid-cols-2 2xl:grid-cols-3 gap-6",
            ),
            class_="space-y-6",
        )

    def _render_card(self, item: Any) -> Any:
        from lexigram.admin.navigation.clusters import cluster_child_href

        child_links = [
            el(
                "a",
                el(
                    "span",
                    child.label,
                    class_="truncate",
                ),
                href=cluster_child_href(child.url),
                class_="block px-3 py-1.5 text-sm text-muted-foreground hover:text-primary-600 dark:hover:text-primary-400 transition-colors",
            )
            for child in item.children
        ]
        return el(
            "div",
            el(
                "a",
                el(
                    "div",
                    self._render_icon(item.icon),
                    class_="w-10 h-10 rounded-lg bg-primary-50 dark:bg-primary-900/30 flex items-center justify-center mb-3",
                ),
                el(
                    "h3",
                    item.label,
                    class_="text-base font-semibold text-foreground",
                ),
                el(
                    "p",
                    _AREA_DESCRIPTIONS.get(
                        item.label.lower(), _DEFAULT_AREA_DESCRIPTION
                    ),
                    class_="text-sm text-muted-foreground mt-1",
                ),
                href=cluster_child_href(item.url),
                class_="block",
            ),
            (
                el("div", *child_links, class_="mt-3 space-y-1")
                if child_links
                else el(
                    "p",
                    "Open area",
                    class_="mt-2 text-sm text-muted-foreground",
                )
            ),
            class_="block bg-card rounded-xl border border-border p-5 hover:border-primary/50 transition-colors",
        )

    def _render_icon(self, icon_name: str) -> Any:
        try:
            from lexigram.ui import get_icon

            return get_icon(
                icon_name, class_name="w-5 h-5 text-primary-600 dark:text-primary-400"
            )
        except (ImportError, ModuleNotFoundError, AttributeError):
            return el("span", "●", class_="text-muted-foreground")
