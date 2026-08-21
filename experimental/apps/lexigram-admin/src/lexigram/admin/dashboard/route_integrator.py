from __future__ import annotations

from collections.abc import Sequence
import inspect
from typing import TYPE_CHECKING, Any

from lexigram.admin.navigation.clusters import (
    CLUSTER_GROUP,
    cluster_child_href,
)
from lexigram.contracts.admin.types import (
    ManagementPageDefinition,
    SettingsPanelDefinition,
)
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.admin.core.routing import AdminRouter
    from lexigram.admin.dashboard.naming_policy import NamingPolicy
    from lexigram.contracts.admin.contributor import BaseAdminContributor

logger = get_logger(__name__)


from lexigram.admin.dashboard.page_handlers import (
    AdminPageHandler,
    _placeholder_page,
    StructuredPageHandler,
    _resolve_handler,
)


def _register_pages(
    router: AdminRouter,
    naming_policy: NamingPolicy,
    prefix: str,
    pages: list[ManagementPageDefinition],
    container: Any = None,
) -> None:
    """Register management page routes on the admin router.

    Routes are registered relative to the admin app mount point
    (the prefix is stripped before registration — the admin router
    already lives under the admin prefix due to ``AdminRouter.mount()``).
    ``registered_internal_paths`` is updated externally so that
    ``_ensure_nav_route`` does not create duplicate placeholders.
    """
    # prefix is intentionally unused — routes live inside the mounted
    # admin app and must be relative to its mount point.
    for page in pages:
        handler = _resolve_handler(page.handler)
        if handler is None:
            continue
        if inspect.isclass(handler) and container is not None:
            handler = AdminPageHandler(handler, container)
        else:
            handler = StructuredPageHandler(handler)
        path = page.route_path
        if not path.startswith("/"):
            path = f"/{path}"
        ns_name = naming_policy.namespaced(page.contributor, page.name)
        naming_policy.register("page", ns_name)
        router.add_route(path=path, method="GET", handler=handler, name=ns_name)


def _register_settings(
    router: AdminRouter,
    naming_policy: NamingPolicy,
    prefix: str,
    panels: list[SettingsPanelDefinition],
    container: Any = None,
) -> None:
    """Register settings panel routes on the admin router.

    Routes are registered relative to the admin app mount point
    (the prefix is stripped before registration — see ``_register_pages``).
    """
    for panel in panels:
        handler = _resolve_handler(panel.handler)
        if handler is None:
            continue
        if inspect.isclass(handler) and container is not None:
            handler = AdminPageHandler(handler, container)
        else:
            handler = StructuredPageHandler(handler)
        path = panel.route_path
        if not path.startswith("/"):
            path = f"/{path}"
        ns_name = naming_policy.namespaced(panel.contributor, panel.name)
        naming_policy.register("panel", ns_name)
        router.add_route(path=path, method="GET", handler=handler, name=ns_name)


class RouteIntegrator:
    """Collects ``AdminRouteSpec``, ``ManagementPageDefinition``, and
    ``SettingsPanelDefinition`` from contributors and registers them
    on the router."""

    def __init__(
        self,
        *,
        router: AdminRouter,
        naming_policy: NamingPolicy,
        route_prefix: str = "",
        container: Any = None,
    ) -> None:
        self._router = router
        self._naming = naming_policy
        self._prefix = route_prefix
        self._container = container

    def register(self, contributors: Sequence[BaseAdminContributor]) -> None:
        """Register each contributor's routes, management pages, and
        settings panels on the admin router.  Nav-item URLs that don't
        have a corresponding handler automatically get a placeholder
        route so they never 404."""
        registered_internal_paths: set[str] = set()

        for c in contributors:
            # Routes
            for spec in c.get_routes():
                ns_name = self._naming.namespaced(c.package_source, spec.name)
                self._naming.register("route", ns_name)
                path = spec.path
                # Contributor specs carry the full URL (e.g. "/admin/...")
                # but routes live inside the mounted admin app, so strip
                # the mount prefix like _ensure_nav_route does.
                if self._prefix and path.startswith(self._prefix):
                    path = path[len(self._prefix) :]
                    if not path:
                        path = "/"
                registered_internal_paths.add(path)
                self._router.add_route(
                    path=path,
                    method=spec.method,
                    handler=spec.handler,
                    name=ns_name,
                )

            # Management pages
            pages = c.get_management_pages()
            if pages:
                for page in pages:
                    internal = page.route_path
                    if not internal.startswith("/"):
                        internal = f"/{internal}"
                    registered_internal_paths.add(internal)
                _register_pages(
                    self._router,
                    self._naming,
                    self._prefix,
                    pages,  # type: ignore[arg-type]
                    container=self._container,
                )

            # Settings panels
            panels = c.get_settings_panels()
            if panels:
                for panel in panels:
                    internal = panel.route_path
                    if not internal.startswith("/"):
                        internal = f"/{internal}"
                    registered_internal_paths.add(internal)
                _register_settings(
                    self._router,
                    self._naming,
                    self._prefix,
                    panels,  # type: ignore[arg-type]
                    container=self._container,
                )

        # Auto-register placeholder routes for nav items without handlers.
        for c in contributors:
            for item in c.get_navigation_items():
                self._ensure_nav_route(item, registered_internal_paths)
                for child in item.children or ():
                    self._ensure_nav_route(child, registered_internal_paths)

        # Cluster areas are also reachable under the center namespace
        # (e.g. /admin/infrastructure/web), mirroring how settings
        # sub-pages nest below /admin/settings. Aliases share the source
        # route's handler — real page or placeholder alike.
        for c in contributors:
            for item in c.get_navigation_items():
                self._register_cluster_alias(item)
                for child in item.children or ():
                    self._register_cluster_alias(child)

    def _ensure_nav_route(
        self,
        item: Any,
        registered_paths: set[str],
    ) -> None:
        """Register a placeholder route for *item* if its URL isn't covered."""
        url = item.url
        if not url or url.startswith("http"):
            return

        internal = url
        if self._prefix and internal.startswith(self._prefix):
            internal = internal[len(self._prefix) :]
        if not internal:
            internal = "/"

        if internal in registered_paths or url in registered_paths:
            return

        safe_label = item.label.lower().replace(" ", "_").replace("/", "_")
        self._router.add_route(
            path=internal,
            method="GET",
            handler=_placeholder_page,
            name=f"placeholder_{safe_label}",
        )
        registered_paths.add(internal)

    def _register_cluster_alias(self, item: Any) -> None:
        """Register a namespaced alias for a cluster group nav item.

        Cluster areas live under the center namespace (``/admin/
        infrastructure/web``) in addition to their contributor URL. When
        the source URL has a real handler, the alias reuses it; otherwise
        the alias falls back to the placeholder page.
        """
        if getattr(item, "group", None) != CLUSTER_GROUP:
            return
        url = item.url
        if not url or url.startswith("http"):
            return
        namespaced = cluster_child_href(url)
        if not namespaced or namespaced == url:
            return

        internal = url
        internal_ns = namespaced
        if self._prefix and internal.startswith(self._prefix):
            internal = internal[len(self._prefix) :]
        if self._prefix and internal_ns.startswith(self._prefix):
            internal_ns = internal_ns[len(self._prefix) :]
        if internal_ns == internal:
            return

        safe_label = item.label.lower().replace(" ", "_").replace("/", "_")
        if not self._router.alias_route(
            internal,
            internal_ns,
            name=f"cluster_alias_{safe_label}",
        ):
            self._router.add_route(
                path=internal_ns,
                method="GET",
                handler=_placeholder_page,
                name=f"cluster_alias_{safe_label}",
            )
