from __future__ import annotations

from collections.abc import Sequence
import inspect
import re
import types
from typing import TYPE_CHECKING, Any, get_args, get_origin, get_type_hints

from starlette.requests import Request as StarletteRequest
from starlette.responses import HTMLResponse

from lexigram.admin.navigation.clusters import (
    CLUSTER_GROUP,
    CLUSTER_ICON,
    CLUSTER_LABEL,
    CLUSTER_URL,
    cluster_child_href,
    cluster_items,
    is_cluster_path,
)
from lexigram.admin.state.context import wants_fragment
from lexigram.contracts.admin.types import (
    ManagementPageDefinition,
    SettingsPanelDefinition,
)
from lexigram.contracts.exceptions import UnresolvableDependencyError
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.admin.core.routing import AdminRouter
    from lexigram.admin.dashboard.naming_policy import NamingPolicy
    from lexigram.contracts.admin.contributor import BaseAdminContributor
    from lexigram.contracts.core.di import ContainerResolverProtocol

logger = get_logger(__name__)


def _strip_optional(tp: Any) -> Any:
    """If *tp* is ``Optional[X]`` (``Union[X, None]`` or ``X | None``),
    return ``X``.  Otherwise return *tp* unchanged."""
    origin = get_origin(tp)
    if origin is types.UnionType:
        args = get_args(tp)
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return non_none[0]
    return tp


_DEFAULT_PRIMARY_COLOR = "#6b7280"

_CLUSTER_HEADER_DESCRIPTION = (
    "Monitor and manage the services powering your application: web, data, "
    "and runtime areas."
)


def _cluster_header_html() -> str:
    """Render the cluster center top-level title + description block.

    Mirrors the settings center header: a ``mb-2`` wrapper with the
    section title and a muted one-line description, rendered above the
    whole center layout (secondary sidebar and page content).
    """
    from lexigram.ui import el, render_to_string

    return render_to_string(
        el(
            "div",
            el("h1", CLUSTER_LABEL, class_="text-2xl font-bold text-foreground"),
            el(
                "p",
                _CLUSTER_HEADER_DESCRIPTION,
                class_="text-muted-foreground mt-1",
            ),
            class_="mb-2",
        )
    )


#: First header block rendered by management pages (h1 + description +
#: divider). Cluster pages have their own top-level header injected by the
#: shell wrapper, so this inline header is dropped.
_PAGE_HEADER_RE = re.compile(
    r"<h1[^>]*>.*?</h1>\s*<p[^>]*>.*?</p>\s*(?:<hr[^>]*/?>)?",
    re.S,
)


async def _resolve_primary_color(container: Any) -> str:
    """Resolve the saved branding primary color, best-effort.

    Falls back to the framework default when no registry/db store is
    available.
    """
    try:
        from lexigram.admin.settings.panel.registry import ConfigRegistry

        registry = await container.resolve(
            ConfigRegistry,
            bypass_visibility=True,
        )
        values = await registry.get_values("admin.branding", "db")
        color = values.get("primary_color")
        if color:
            return str(color)
    except Exception:  # noqa: BLE001 — non-fatal
        logger.exception("admin.theme_overrides_failed")
    return _DEFAULT_PRIMARY_COLOR


class AdminPageHandler:
    """ASGI adapter that resolves a management page handler from the DI
    container at request time and delegates to its ``handle()`` method.

    Starlette treats class endpoints as ASGI apps — it calls
    ``cls(scope, receive, send)`` which becomes ``__init__(scope, receive,
    send)``.  Management page handlers use keyword-only constructor DI
    (``def __init__(self, *, repo: ..., ...)``), so direct registration
    always raises TypeError.  This wrapper sidesteps that by storing the
    page **class** at route-build time and resolving an instance from the
    container at request time.
    """

    def __init__(
        self,
        page_cls: type,
        container: ContainerResolverProtocol,
    ) -> None:
        self._page_cls = page_cls
        self._container = container

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        request = StarletteRequest(scope, receive, send)
        try:
            instance = await self._resolve_page()
            response = await instance.handle(request)
        except Exception:
            logger.exception(
                "admin_page_handler_error",
                page=self._page_cls.__name__,
            )
            response = await _placeholder_page(request, self._container)

        try:
            is_htmx = wants_fragment(request)
        except KeyError:
            is_htmx = False
        if isinstance(response, HTMLResponse):
            response = await self._apply_cluster_header(request, response)
        if not is_htmx and isinstance(response, HTMLResponse):
            response = await self._wrap_in_shell(request, response)

        await response(scope, receive, send)

    async def _apply_cluster_header(
        self,
        request: StarletteRequest,
        response: HTMLResponse,
    ) -> HTMLResponse:
        """Drop the page's own inline title/description block.

        Cluster pages receive a single top-level header rendered above
        the whole center layout (see ``_cluster_header_html``), so the
        page's inline header is removed. Only applies to pages living
        inside a cluster center (e.g. ``/admin/infrastructure/...``).
        """
        state = getattr(request, "app", None)
        groups = (
            getattr(state.state, "assembler_groups", None)
            if state and hasattr(state, "state")
            else None
        )
        if not is_cluster_path(request.url.path, cluster_items(groups)):
            return response

        content = (
            response.body.decode()
            if isinstance(response.body, bytes)
            else str(response.body)
        )
        return HTMLResponse(_PAGE_HEADER_RE.sub("", content, count=1))

    async def _wrap_in_shell(
        self,
        request: StarletteRequest,
        response: HTMLResponse,
    ) -> HTMLResponse:
        from pathlib import Path

        from starlette.templating import Jinja2Templates

        from lexigram.admin.engine.renderer import resolve_admin_nav
        from lexigram.admin.ui.templates.shell import AdminShell
        from lexigram.ui import raw, render_to_string

        content = (
            response.body.decode()
            if isinstance(response.body, bytes)
            else str(response.body)
        )

        title = self._page_cls.__name__.removesuffix("Page")

        user = (
            getattr(request.state, "user", None) if hasattr(request, "state") else None
        )
        nav_items, system_menu_items, secondary_nav = resolve_admin_nav(request)
        state = getattr(request, "app", None)
        groups = (
            getattr(state.state, "assembler_groups", None)
            if state and hasattr(state, "state")
            else None
        )
        is_cluster = is_cluster_path(request.url.path, cluster_items(groups))
        if secondary_nav:
            from lexigram.admin.ui.organisms.secondary_nav import ClusterLayout

            content = render_to_string(
                ClusterLayout(items=secondary_nav, content=raw(content))
            )
            if is_cluster:
                content = _cluster_header_html() + content

        breadcrumbs: list[dict[str, str]] | None = None
        if secondary_nav and is_cluster:
            breadcrumbs = [
                {"label": "Home", "url": "/admin/"},
                {"label": CLUSTER_LABEL, "url": CLUSTER_URL},
            ]
            path = request.url.path
            for item in secondary_nav:
                item_href = item.get("href", "")
                if path == item_href:
                    breadcrumbs.append({"label": item.get("label", ""), "url": ""})
                    title = item.get("label", title)
                    break
                child = next(
                    (c for c in item.get("children", []) if path == c.get("href", "")),
                    None,
                )
                if child is not None:
                    breadcrumbs.append(
                        {"label": item.get("label", ""), "url": item_href}
                    )
                    breadcrumbs.append({"label": child.get("label", ""), "url": ""})
                    title = child.get("label", title)
                    break

        theme_css = ""
        try:
            from lexigram.admin.theme.service import AdminThemeService

            service = AdminThemeService(
                primary_color=await _resolve_primary_color(self._container)
            )
            theme_css = service.generate_theme_css()
        except Exception:  # noqa: BLE001 — non-fatal
            pass

        user_menu_items: list[dict[str, str]] = [
            {
                "label": CLUSTER_LABEL,
                "href": CLUSTER_URL,
                "icon": CLUSTER_ICON,
            },
            {
                "label": "Plugins",
                "href": "/admin/plugins",
                "icon": "plugins",
            },
            {
                "label": "Settings",
                "href": "/admin/settings",
                "icon": "settings",
            },
        ]

        branding: dict[str, str] = {}
        try:
            from lexigram.admin.multitenancy.adapter import resolve_tenant_id
            from lexigram.admin.services.settings_service import (
                resolve_admin_settings_service,
            )

            container = (
                getattr(request.state, "root_container", None)
                or getattr(request.state, "container", None)
                or getattr(request.app.state, "container", None)
                or self._container
            )
            settings_service = await resolve_admin_settings_service(container)
            if settings_service is not None:
                tenant = await resolve_tenant_id(request, default="default")
                overrides = await settings_service.get_all(tenant)
                for field in ("primary_color", "site_name", "logo_url", "dark_mode"):
                    value = overrides.get(field) or overrides.get(
                        f"admin.branding.{field}"
                    )
                    if value:
                        branding[field] = value
                if branding.get("primary_color"):
                    from lexigram.admin.theme.service import AdminThemeService

                    theme_css = AdminThemeService(
                        primary_color=branding["primary_color"]
                    ).generate_theme_css()
        except Exception:  # noqa: BLE001 — non-fatal
            pass

        shell = AdminShell(
            content=content,
            title=title,
            user=user,
            nav_items=nav_items,
            system_menu_items=system_menu_items,
            user_menu_items=user_menu_items,
            breadcrumbs=breadcrumbs,
            theme_css=theme_css,
            **{
                k: v
                for k, v in branding.items()
                if k in ("dark_mode", "site_name", "logo_url")
            },
        )
        shell_html = render_to_string(shell)

        templates_dir = Path(__file__).resolve().parent.parent / "views" / "templates"
        templates = Jinja2Templates(directory=str(templates_dir))
        return templates.TemplateResponse(
            request,
            "admin_shell.html",
            context={
                "content": shell_html,
                "title": title,
                "dark_mode": branding.get("dark_mode", ""),
            },
        )

    async def _resolve_page(self) -> Any:
        """Resolve page instance from container.

        Uses ``container.call(cls.__init__)`` to resolve each constructor
        parameter from the DI container, then constructs the instance
        manually.  This is necessary because ``get_type_hints(cls)``
        returns an empty dict for classes with ``from __future__ import
        annotations`` (PEP 563), so ``container.call(cls)`` cannot
        discover parameter types.
        """
        init_method = self._page_cls.__init__  # type: ignore[misc]
        sig = inspect.signature(init_method)
        hints = get_type_hints(init_method)
        kwargs: dict[str, Any] = {}
        for name, param in sig.parameters.items():
            if name == "self":
                continue
            if param.kind in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            ):
                continue
            param_type = hints.get(name)
            if param_type is not None:
                try:
                    resolution_target = _strip_optional(param_type)
                    kwargs[name] = await self._container.resolve(resolution_target)
                    continue
                except UnresolvableDependencyError:
                    pass
            if param.default is not inspect.Parameter.empty:
                kwargs[name] = param.default
            elif param_type is not None:
                raise UnresolvableDependencyError(
                    f"Cannot resolve parameter {name!r} for "
                    f"{self._page_cls.__name__}: type {param_type} not registered.",
                )
            else:
                raise UnresolvableDependencyError(
                    f"Cannot resolve parameter {name!r} for "
                    f"{self._page_cls.__name__}: no type hint and no default.",
                )
        return self._page_cls(**kwargs)


async def _placeholder_page(
    request: Any,
    container: Any | None = None,
) -> HTMLResponse:
    """Placeholder for admin pages without an implemented handler.

    For HTMX requests returns only the content fragment (no shell) so
    the sidebar/topbar from the existing page stays intact.  For direct
    navigation returns the full admin layout.

    Args:
        request: Starlette request.
        container: Optional resolver for theme settings.
    """
    content = (
        '<div class="flex items-center justify-center h-64">'
        '<div class="text-center">'
        '<h2 class="text-xl font-semibold text-muted-foreground">Under Construction</h2>'
        '<p class="text-muted-foreground mt-2">This page has not been implemented yet.</p>'
        "</div></div>"
    )

    try:
        from lexigram.admin.engine.renderer import resolve_admin_nav

        nav_items, system_menu_items, secondary_nav = resolve_admin_nav(request)
    except Exception:  # noqa: BLE001 — non-fatal
        nav_items, system_menu_items, secondary_nav = [], [], None

    if secondary_nav:
        from lexigram.admin.ui.organisms.secondary_nav import ClusterLayout
        from lexigram.ui import raw, render_to_string

        content = render_to_string(
            ClusterLayout(items=secondary_nav, content=raw(content))
        )

    is_htmx = wants_fragment(request)

    if is_htmx:
        return HTMLResponse(content)

    try:
        from pathlib import Path

        from starlette.templating import Jinja2Templates

        from lexigram.admin.ui.templates.shell import AdminShell
        from lexigram.ui import render_to_string

        user = (
            getattr(request.state, "user", None) if hasattr(request, "state") else None
        )

        user_menu_items = [
            {
                "label": CLUSTER_LABEL,
                "href": CLUSTER_URL,
                "icon": CLUSTER_ICON,
            },
            {
                "label": "Settings",
                "href": "/admin/settings",
                "icon": "settings",
            },
        ]

        theme_css = ""
        try:
            from lexigram.admin.theme.service import AdminThemeService

            service = AdminThemeService(
                primary_color=(
                    await _resolve_primary_color(container)
                    if container is not None
                    else _DEFAULT_PRIMARY_COLOR
                )
            )
            theme_css = service.generate_theme_css()
        except Exception:  # noqa: BLE001 — non-fatal
            pass

        shell = AdminShell(
            content=content,
            title="Under Construction",
            user=user,
            nav_items=nav_items,
            system_menu_items=system_menu_items,
            user_menu_items=user_menu_items,
            theme_css=theme_css,
        )
        shell_html = render_to_string(shell)

        templates_dir = Path(__file__).resolve().parent.parent / "views" / "templates"
        templates = Jinja2Templates(directory=str(templates_dir))
        return templates.TemplateResponse(
            request,
            "admin_shell.html",
            context={
                "content": shell_html,
                "title": "Under Construction",
                "dark_mode": "",
            },
        )
    except Exception:
        return HTMLResponse(content)


def _resolve_handler(handler: Any) -> Any:
    """Resolve a string dotted-path handler to the actual callable."""
    if not isinstance(handler, str):
        return handler
    try:
        module_path, _, func_name = handler.partition(":")
        mod = __import__(module_path, fromlist=[func_name])
        resolved = getattr(mod, func_name, None)
        if resolved is None:
            logger.warning("handler_import_failed", handler=handler)
        return resolved
    except Exception:  # noqa: BLE001
        logger.warning("handler_import_failed", handler=handler, exc_info=True)
        return None


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
                registered_internal_paths.add(spec.path)
                self._router.add_route(
                    path=spec.path,
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
