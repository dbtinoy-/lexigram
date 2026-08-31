"""Generic cluster center controller — landing page for any cluster.

Shows an overview of the areas contributed to the cluster's navigation
group as linked cards. The secondary nav column renders inside the content
section next to the overview (settings ConfigLayout pattern). One instance
is mounted per registered cluster; the cluster's ``slug`` forms the URL
segment (``/admin/{slug}``) and its group drives which contributed items
are listed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from starlette.requests import Request
from starlette.responses import Response

from lexigram.admin.clusters.base import Cluster
from lexigram.admin.clusters.registry import INFRASTRUCTURE_CLUSTER
from lexigram.admin.controllers.base import AdminController
from lexigram.contracts.web import get
from lexigram.logging import get_logger
from lexigram.ui import el

if TYPE_CHECKING:
    from lexigram.admin.engine.renderer import AdminRenderer
    from lexigram.admin.services.settings_service import AdminSettingsService

logger = get_logger(__name__)

__all__ = ["ClusterCenterController"]

_AREA_DESCRIPTIONS: dict[str, str] = {
    "web": "HTTP routing, middleware, and web API endpoints.",
    "sql": "Database connections, queries, and schema management.",
    "cache": "Cache backends, keys, and TTL policies.",
    "events": "Event bus, subscriptions, and message delivery.",
    "queue": "Background job queue and worker management.",
    "tasks": "Scheduled tasks, cron jobs, and automation.",
}

_DEFAULT_AREA_DESCRIPTION = "Manage and monitor this infrastructure area."


class ClusterCenterController(AdminController):
    """Landing page for a cluster center.

    Routes:
        GET /admin/{slug}  - Overview of cluster areas
    """

    prefix = "/cluster"

    def __init__(
        self,
        renderer: AdminRenderer,
        cluster: Cluster = INFRASTRUCTURE_CLUSTER,
        settings_service: AdminSettingsService | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(renderer=renderer, settings_service=settings_service, **kwargs)
        self._cluster = cluster
        self.prefix = f"/{cluster.slug}"

    @get("/")
    async def index(self, request: Request) -> Response:
        from lexigram.admin.engine.renderer import resolve_admin_nav
        from lexigram.admin.navigation.clusters import cluster_items
        from lexigram.admin.resources.urls import admin_prefix_from_request, admin_url
        from lexigram.admin.ui.organisms.secondary_nav import ClusterLayout
        from lexigram.ui import render_to_string

        state = getattr(request, "app", None)
        groups = (
            getattr(state.state, "assembler_groups", None)
            if state and hasattr(state, "state")
            else None
        )
        cluster = self._cluster
        admin_prefix = admin_prefix_from_request(request)
        content = self._render_overview(
            cluster_items(groups, cluster=cluster), admin_prefix=admin_prefix
        )
        _, _, secondary_nav = resolve_admin_nav(request)
        if secondary_nav:
            content = render_to_string(
                ClusterLayout(items=secondary_nav, content=content)
            )
        else:
            content = render_to_string(content)
        content = render_to_string(self._render_header()) + content
        return await self.render_admin(
            request,
            content,
            title=str(cluster.label),
            breadcrumbs=self.generate_breadcrumbs(
                ("Home", admin_url(admin_prefix, "")),
                current=str(cluster.label),
            ),
        )

    def _render_header(self) -> Any:
        return el(
            "div",
            el(
                "h1",
                self._cluster.label,
                class_="text-2xl font-bold text-foreground",
            ),
            el(
                "p",
                self._cluster.description or "Manage and monitor this cluster's areas.",
                class_="text-muted-foreground mt-1",
            ),
            class_="mb-2",
        )

    def _render_overview(
        self, items: list[Any], *, admin_prefix: str = "/admin"
    ) -> Any:
        if not items:
            # An empty cluster is a configuration state, not a failure, so
            # the copy says what produces areas here instead of leaving the
            # operator on a dead end with nothing to act on.
            return el(
                "div",
                el("div", "⚙️", class_="text-5xl mb-4", aria_hidden="true"),
                el(
                    "h3",
                    f"No {self._cluster.label} areas yet",
                    class_="text-lg font-semibold text-foreground",
                ),
                el(
                    "p",
                    (
                        "Areas appear here when a package contributes "
                        f"navigation to the '{self._cluster.group}' group. "
                        "Install or enable a package that provides one."
                    ),
                    class_="text-muted-foreground mt-2 max-w-md mx-auto",
                ),
                class_="text-center py-16",
                role="status",
            )

        cards = [self._render_card(item, admin_prefix=admin_prefix) for item in items]
        return el(
            "div",
            el(
                "div",
                *cards,
                class_="grid grid-cols-1 md:grid-cols-2 2xl:grid-cols-3 gap-6",
            ),
            class_="p-6",
        )

    def _render_card(self, item: Any, *, admin_prefix: str = "/admin") -> Any:
        from lexigram.admin.navigation.clusters import cluster_child_href

        cluster = self._cluster
        child_links = [
            el(
                "li",
                el(
                    "a",
                    el("span", child.label, class_="truncate"),
                    href=cluster_child_href(
                        child.url, cluster=cluster, admin_prefix=admin_prefix
                    ),
                    class_=(
                        "block rounded px-3 py-1.5 text-sm text-muted-foreground "
                        "hover:text-primary-600 hover:bg-muted "
                        "dark:hover:text-primary-400 transition-colors "
                        "focus-visible:outline-none focus-visible:ring-2 "
                        "focus-visible:ring-ring"
                    ),
                ),
            )
            for child in item.children
        ]
        description = _AREA_DESCRIPTIONS.get(
            str(item.label).lower(), _DEFAULT_AREA_DESCRIPTION
        )
        # The heading link is stretched over the whole card so the entire
        # tile is a click target, which is what the card-wide hover style
        # already implied. Child links sit above it in the stacking order so
        # they stay independently clickable, and they remain real list items
        # rather than being nested inside the card link, which is invalid
        # markup and collapses keyboard navigation.
        return el(
            "div",
            el(
                "div",
                self._render_icon(item.icon),
                class_=(
                    "w-10 h-10 rounded-lg bg-primary-50 dark:bg-primary-900/30 "
                    "flex items-center justify-center mb-3"
                ),
            ),
            el(
                "h3",
                el(
                    "a",
                    item.label,
                    href=cluster_child_href(
                        item.url, cluster=cluster, admin_prefix=admin_prefix
                    ),
                    # `stretched-link` rather than Tailwind's
                    # after:content-[''] arbitrary value: the quotes in that
                    # class are HTML-escaped on render, so the emitted
                    # attribute no longer matches the generated CSS.
                    class_=(
                        "stretched-link rounded focus-visible:outline-none "
                        "focus-visible:ring-2 focus-visible:ring-ring"
                    ),
                ),
                class_="text-base font-semibold text-foreground",
            ),
            el("p", description, class_="text-sm text-muted-foreground mt-1"),
            (
                el(
                    "ul",
                    *child_links,
                    class_="relative mt-3 space-y-1",
                    aria_label=f"{item.label} sections",
                )
                if child_links
                else ""
            ),
            class_=(
                "cluster-card relative bg-card rounded-xl border border-border "
                "p-5 hover:border-primary/50 hover:shadow-sm "
                "focus-within:border-primary/50 transition-colors"
            ),
        )

    def _render_icon(self, icon_name: str) -> Any:
        try:
            from lexigram.ui import get_icon

            # get_icon already emits its own `size` classes; repeating them
            # in class_name rendered a duplicated "w-5 h-5 w-5 h-5".
            return get_icon(
                icon_name,
                class_name="text-primary-600 dark:text-primary-400",
                **{"aria-hidden": "true", "focusable": "false"},
            )
        except (ImportError, ModuleNotFoundError, AttributeError):
            return el("span", "●", class_="text-muted-foreground", aria_hidden="true")
