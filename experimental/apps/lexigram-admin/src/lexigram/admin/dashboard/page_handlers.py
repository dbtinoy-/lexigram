from __future__ import annotations

import inspect
import re
import types
from typing import TYPE_CHECKING, Any, cast, get_args, get_origin, get_type_hints

from markupsafe import Markup
from starlette.requests import Request as StarletteRequest
from starlette.responses import HTMLResponse

from lexigram.admin.dashboard.page_fallbacks import (
    _placeholder_page,
    _resolve_primary_color,
)
from lexigram.admin.navigation.clusters import (
    CLUSTER_LABEL,
    CLUSTER_URL,
    cluster_items,
    is_cluster_path,
)
from lexigram.admin.state.context import wants_fragment
from lexigram.contracts.admin.page_content import PageContent
from lexigram.contracts.admin.widget_content import EmptyContent
from lexigram.contracts.exceptions import UnresolvableDependencyError
from lexigram.logging import get_logger

if TYPE_CHECKING:
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
            if not isinstance(response, HTMLResponse):
                from lexigram.admin.dashboard.page_renderer import (
                    render_page_content,
                )
                from lexigram.contracts.admin.page_content import PageContent

                if isinstance(response, PageContent):
                    response = render_page_content(response)
                else:
                    logger.error(
                        "admin_page_contract_violation",
                        page=self._page_cls.__name__,
                        result_type=type(response).__name__,
                    )
                    response = await _placeholder_page(request, self._container)
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
        from lexigram.admin.resources.urls import admin_prefix_from_request

        if not is_cluster_path(
            request.url.path,
            cluster_items(groups),
            admin_prefix=admin_prefix_from_request(request),
        ):
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
        from lexigram.admin.navigation.manager import NavigationManager
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
        from lexigram.admin.resources.urls import admin_prefix_from_request, admin_url

        admin_prefix = admin_prefix_from_request(request)
        is_cluster = is_cluster_path(
            request.url.path,
            cluster_items(groups),
            admin_prefix=admin_prefix,
        )
        active_cluster = NavigationManager(request).active_cluster()
        cluster_label = getattr(active_cluster, "label", CLUSTER_LABEL)
        cluster_url = admin_url(
            admin_prefix,
            getattr(active_cluster, "slug", None)
            or CLUSTER_URL.rstrip("/").rsplit("/", 1)[-1],
        )
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
                {"label": "Home", "url": admin_url(admin_prefix, "")},
                {"label": cluster_label, "url": cluster_url},
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
        except Exception:  # noqa: BLE001, S110 — non-fatal
            pass

        from lexigram.admin.navigation.manager import NavigationManager

        user_menu_items: list[dict[str, str | None]] = (
            NavigationManager(request).user_menu_items() if request is not None else []
        )

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
        except Exception:  # noqa: BLE001, S110 — non-fatal
            pass

        from lexigram.admin.resources.urls import admin_prefix_from_request

        shell = AdminShell(
            content=content,
            title=title,
            user=user,
            nav_items=nav_items,
            system_menu_items=system_menu_items,
            user_menu_items=user_menu_items,
            breadcrumbs=breadcrumbs,
            theme_css=theme_css,
            admin_prefix=(
                admin_prefix_from_request(request) if request is not None else "/admin"
            ),
            **cast(
                "Any",
                {
                    k: v
                    for k, v in branding.items()
                    if k in ("dark_mode", "site_name", "logo_url")
                },
            ),
        )
        shell_html = render_to_string(shell)

        templates_dir = Path(__file__).resolve().parent.parent / "views" / "templates"
        templates = Jinja2Templates(directory=str(templates_dir))
        return templates.TemplateResponse(
            request,
            "admin_shell.html",
            context={
                "content": Markup(shell_html),  # noqa: S704 — framework-composed trusted HTML
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


class StructuredPageHandler:
    """Wrap management page handlers so only ``PageContent`` reaches the browser.

    Starlette treats class endpoints as ASGI apps (``__call__(scope, receive,
    send)``), so this wrapper builds a ``StarletteRequest`` from the ASGI scope
    before delegating to the page handler.

    Any other return (str, HTMLResponse, template, ...) is a contract
    violation: it is logged and replaced with an error page.
    """

    def __init__(self, handler: Any) -> None:
        self._handler = handler

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        from lexigram.admin.dashboard.page_renderer import render_page_content

        request = StarletteRequest(scope, receive, send)
        handler = self._handler
        callable_handler = handler.handle if hasattr(handler, "handle") else handler
        result = await callable_handler(request)
        if isinstance(result, PageContent):
            response = render_page_content(result)
        else:
            logger.error(
                "page_contract_violation",
                handler=type(self._handler).__name__,
                result_type=type(result).__name__,
            )
            response = render_page_content(
                PageContent(
                    title="Page Contract Violation",
                    body=EmptyContent(
                        title="Invalid Page Content",
                        message=(
                            "The page handler returned raw HTML. "
                            "Convert it to PageContent."
                        ),
                        icon="alert-triangle",
                    ),
                )
            )
        await response(scope, receive, send)
