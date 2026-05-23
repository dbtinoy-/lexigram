from __future__ import annotations

from collections.abc import Sequence
import inspect
import types
from typing import TYPE_CHECKING, Any, get_args, get_origin, get_type_hints

from starlette.requests import Request as StarletteRequest
from starlette.responses import HTMLResponse

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
        pass
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
            is_htmx = bool(request.headers.get("hx-request"))
        except KeyError:
            is_htmx = False
        if not is_htmx and isinstance(response, HTMLResponse):
            response = await self._wrap_in_shell(request, response)

        await response(scope, receive, send)

    async def _wrap_in_shell(
        self,
        request: StarletteRequest,
        response: HTMLResponse,
    ) -> HTMLResponse:
        from pathlib import Path

        from starlette.templating import Jinja2Templates

        from lexigram.admin.engine.renderer import resolve_admin_nav
        from lexigram.admin.ui.templates.shell import AdminShell
        from lexigram.ui import render_to_string

        content = (
            response.body.decode()
            if isinstance(response.body, bytes)
            else str(response.body)
        )

        title = self._page_cls.__name__.removesuffix("Page")

        user = (
            getattr(request.state, "user", None) if hasattr(request, "state") else None
        )
        nav_items, system_menu_items = resolve_admin_nav(request)

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
                "label": "Settings",
                "href": "/admin/settings",
                "icon": "settings",
            },
        ]

        shell = AdminShell(
            content=content,
            title=title,
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
            context={"content": shell_html, "title": title},
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

    is_htmx = bool(request.headers.get("hx-request"))

    if is_htmx:
        return HTMLResponse(content)

    try:
        from pathlib import Path

        from starlette.templating import Jinja2Templates

        from lexigram.admin.engine.renderer import resolve_admin_nav
        from lexigram.admin.ui.templates.shell import AdminShell
        from lexigram.ui import render_to_string

        user = (
            getattr(request.state, "user", None) if hasattr(request, "state") else None
        )
        nav_items, system_menu_items = resolve_admin_nav(request)

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
            theme_css=theme_css,
        )
        shell_html = render_to_string(shell)

        templates_dir = Path(__file__).resolve().parent.parent / "views" / "templates"
        templates = Jinja2Templates(directory=str(templates_dir))
        return templates.TemplateResponse(
            request,
            "admin_shell.html",
            context={"content": shell_html, "title": "Under Construction"},
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
