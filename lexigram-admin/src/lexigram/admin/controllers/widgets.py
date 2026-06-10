"""Widget controller — routes HTMX widget requests to contributors."""

from __future__ import annotations

import inspect
from typing import Any, cast

from starlette.requests import Request
from starlette.routing import Route

from lexigram.admin.auth.protocols import (
    AdminAuditLogServiceProtocol,
    AdminCsrfServiceProtocol,
)
from lexigram.admin.auth.types import AdminSecurityEventType
from lexigram.admin.config import AdminRbacConfig
from lexigram.admin.dashboard.content_renderer import render_content
from lexigram.admin.dashboard.widget_types import ConfigField
from lexigram.admin.params import parse_widget_params
from lexigram.admin.rbac.super_admin import is_super_admin
from lexigram.contracts.admin.protocols import AdminContributorRegistryProtocol
from lexigram.contracts.admin.types import WidgetContent
from lexigram.contracts.web import get, post
from lexigram.di.decorators import inject
from lexigram.logging import get_logger
from lexigram.ui import el

logger = get_logger(__name__)

_REQUIRED_PERMISSIONS = frozenset({"admin.settings.edit"})


@inject
class WidgetController:
    """Routes HTMX widget/health requests to the appropriate contributor.

    All dependencies are constructor-injected. No service locator.

    Args:
        registry: The admin contributor registry.
    """

    prefix = ""

    def __init__(
        self,
        registry: AdminContributorRegistryProtocol,
        audit_service: AdminAuditLogServiceProtocol | None = None,
        csrf_service: AdminCsrfServiceProtocol | None = None,
        rbac_config: AdminRbacConfig | None = None,
    ) -> None:
        self._registry = registry
        self._settings_service: Any = None
        self._resolver: Any = None
        self._audit_service = audit_service
        self._csrf_service = csrf_service
        self._rbac_config = rbac_config

    def _get_csrf_token(self, request: Request) -> str | None:
        """Resolve the CSRF token for form rendering, if available."""
        if not self._csrf_service:
            return None
        try:
            session = getattr(request, "session", {})
            session_id: str = session.get("admin_user_id", "")
            return self._csrf_service.generate_token(session_id)
        except Exception:  # noqa: BLE001 — non-fatal for form rendering
            return None

    # -- helpers --

    def _user_has_edit_permission(self, request: Request) -> bool:
        """Check whether the requesting user may mutate widget prefs.

        Superadmin bypasses permission gating so accounts created with an
        empty permission set (e.g. via the setup wizard) can still manage
        dashboard widgets.
        """
        user = getattr(getattr(request, "state", None), "user", None)
        if self._user_is_superadmin(request):
            return True
        permissions = frozenset(getattr(user, "permissions", None) or ())
        return permissions.issuperset(_REQUIRED_PERMISSIONS)

    def _user_permissions(self, request: Request) -> frozenset[str]:
        """Return the requesting user's permission set (empty when absent)."""
        user = getattr(getattr(request, "state", None), "user", None)
        return frozenset(getattr(user, "permissions", None) or ())

    def _user_is_superadmin(self, request: Request) -> bool:
        """Return True when the requesting user holds the superadmin role."""
        role = (self._rbac_config or AdminRbacConfig()).super_admin_role
        user = getattr(getattr(request, "state", None), "user", None)
        return bool(user) and is_super_admin(user, role)

    def _has_required_permission(self, request: Request, required: str | None) -> bool:
        """Check *required* against the requesting user; superadmin bypasses."""
        if not required:
            return True
        if self._user_is_superadmin(request):
            return True
        return required in self._user_permissions(request)

    async def _audit(
        self,
        request: Request,
        success: bool = True,
        event_type: AdminSecurityEventType = AdminSecurityEventType.SETTINGS_UPDATED,
        **metadata: Any,
    ) -> None:
        """Append a widget-prefs change to the security audit log, best-effort."""
        if not self._audit_service:
            return
        try:
            client = getattr(request, "client", None)
            await self._audit_service.log_event(
                event_type=event_type,
                ip_address=getattr(client, "host", "unknown"),
                user_agent=request.headers.get("user-agent", "") or "",
                success=success,
                metadata=metadata,
            )
        except Exception:  # noqa: BLE001 — audit failures must not break saves
            logger.warning("widgets.audit_failed", **metadata)

    def get_routes(self) -> list[Any]:
        """Extract decorated routes from this controller instance."""
        routes = []

        for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            if hasattr(method, "_route_config"):
                config = method._route_config
                method_params = list(inspect.signature(method).parameters.keys())

                async def starlette_handler(
                    request: Request, m=method, params=method_params
                ) -> Any:
                    kwargs = {"request": request}
                    for param in params:
                        if param == "request":
                            continue
                        if param in request.path_params:
                            kwargs[param] = request.path_params[param]
                    return await m(**kwargs)

                base_path = getattr(self, "prefix", "").rstrip("/")
                route_path = config["path"]
                if not route_path.startswith("/"):
                    route_path = f"/{route_path}"

                if route_path == "/" and base_path:
                    full_path = base_path
                else:
                    full_path = f"{base_path}{route_path}" if base_path else route_path

                routes.append(
                    Route(
                        full_path,
                        endpoint=starlette_handler,
                        methods=[config["method"]],
                        name=config.get("name") or f"admin_widget_{name}",
                    ),
                )

        return routes

    @get("/{contributor_id}/widgets/{widget_name}")
    async def render_widget(
        self,
        request: Request,
        contributor_id: str,
        widget_name: str,
    ) -> object:
        """Render a widget fragment for the HTMX dashboard.

        Returns an inline error card when the widget is not found or fails
        to render, rather than returning an HTTP error status. This lets
        the dashboard grid maintain its layout even when individual widgets
        fail.
        """
        from starlette.responses import HTMLResponse

        contributor = self._registry.get(contributor_id)
        if contributor is None:
            logger.warning(
                "widget_contributor_not_found",
                contributor_id=contributor_id,
                widget_name=widget_name,
            )
            return HTMLResponse(
                self._render_error_card(
                    f"Contributor '{contributor_id}' not found",
                    contributor_id=contributor_id,
                    widget_name=widget_name,
                ),
                status_code=200,
            )

        widget_def = next(
            (w for w in contributor.get_dashboard_widgets() if w.name == widget_name),
            None,
        )
        if widget_def is not None and not self._has_required_permission(
            request, widget_def.permission
        ):
            return HTMLResponse(
                self._render_error_card(
                    "You do not have permission to view this widget.",
                    contributor_id=contributor_id,
                    widget_name=widget_name,
                ),
                status_code=200,
            )

        params = parse_widget_params(dict(request.query_params))

        if self._settings_service:
            full_name = f"{contributor_id}.{widget_name}"
            prefs = await self._settings_service.get_widget_prefs("default", "default")
            cfg = prefs.get("configs", {}).get(full_name, {})
            if "time_window_minutes" in cfg:
                from lexigram.contracts.admin.types import WidgetParams

                params = WidgetParams(
                    page=params.page,
                    page_size=params.page_size,
                    time_window_minutes=int(cfg["time_window_minutes"]),
                    raw=params.raw,
                )

        result = await contributor.render_widget(
            widget_name, params, resolver=self._resolver
        )

        if result.is_ok():
            vm = result.unwrap()
            return HTMLResponse(self._wrap_widget_body(vm.content, vm.title, vm.error))

        error = result.unwrap_err()
        logger.error(
            "widget_render_failed",
            contributor_id=contributor_id,
            widget_name=widget_name,
            error=str(error),
        )
        return HTMLResponse(
            self._render_error_card(
                str(error),
                contributor_id=contributor_id,
                widget_name=widget_name,
            ),
            status_code=200,
        )

    @staticmethod
    def _wrap_widget_body(
        content: WidgetContent,
        title: str | None = None,
        error: str | None = None,
    ) -> str:
        """Wrap widget body in a container with optional error banner."""
        from lexigram.ui.core.base import el, raw, render_to_string

        inner = render_content(content)
        children: list[object] = []
        if title:
            children.append(
                el(
                    "div",
                    title,
                    class_="widget-title text-xs font-semibold text-muted-foreground mb-1",
                )
            )
        if error:
            children.append(
                el(
                    "div",
                    error,
                    class_="text-xs text-destructive bg-destructive/10 rounded px-2 py-1 mb-2",
                )
            )
        children.append(el("div", raw(inner), class_="widget-content"))
        return render_to_string(el("div", *children, class_="widget-body-container"))

    @staticmethod
    def _render_error_card(
        message: str,
        contributor_id: str | None = None,
        widget_name: str | None = None,
    ) -> str:
        """Render an inline error card for failed widget rendering."""
        from lexigram.ui.core.base import el, render_to_string

        data_attrs: dict[str, str] = {}
        if contributor_id:
            data_attrs["data-contributor-id"] = contributor_id
        if widget_name:
            data_attrs["data-widget-name"] = widget_name

        return render_to_string(
            el(
                "div",
                el(
                    "div",
                    class_="text-destructive text-lg mb-1",
                ),
                el(
                    "p",
                    message,
                    class_="text-sm text-muted-foreground",
                ),
                class_="widget-error-card bg-destructive/10 border border-destructive/30 rounded-lg p-4 text-center",
                **data_attrs,
            )
        )

    @get("/{contributor_id}/health/{check_name}")
    async def render_health_check(
        self,
        request: Request,
        contributor_id: str,
        check_name: str,
    ) -> object:
        """Render a health check fragment for the HTMX dashboard."""
        from starlette.responses import HTMLResponse, Response

        contributor = self._registry.get(contributor_id)
        if contributor is None:
            return Response(
                content=f"Contributor '{contributor_id}' not found",
                status_code=404,
            )

        health_def = next(
            (h for h in contributor.get_health_definitions() if h.name == check_name),
            None,
        )
        if health_def is not None and not self._has_required_permission(
            request, health_def.permission
        ):
            return Response(content="Permission denied", status_code=403)

        result = await contributor.render_health_check(check_name)

        if result.is_ok():
            return HTMLResponse(render_content(result.unwrap()))

        error = result.unwrap_err()
        return Response(content=str(error), status_code=422)

    @get("/core/widgets/{name}/config")
    async def widget_config_popup(
        self,
        request: Request,
        name: str,
    ) -> object:
        """Render config popup for a widget."""
        from starlette.responses import HTMLResponse

        from lexigram.admin.dashboard.widgets import render_widget_config_popup

        tenant_id = "default"
        user_id = "default"

        widget_def = None
        contributor = None
        for c in self._registry.get_all():
            for wdef in c.get_dashboard_widgets():
                if wdef.name == name:
                    widget_def = wdef
                    contributor = c
                    break
            if widget_def:
                break

        if widget_def is None:
            return HTMLResponse("Widget not found", status_code=404)

        schema: list[ConfigField] = getattr(
            contributor, "get_widget_config_schema", lambda _: []
        )(name)

        prefs = (
            await self._settings_service.get_widget_prefs(tenant_id, user_id)
            if self._settings_service
            else {}
        )
        enabled = "enabled" not in prefs or name in prefs.get("enabled", [])
        cfg = prefs.get("configs", {}).get(name, {})

        html = render_widget_config_popup(name, widget_def.title, schema, cfg, enabled)
        return HTMLResponse(html)

    @post("/core/widgets/config")
    async def save_widget_config(self, request: Request) -> object:
        """Save a single widget's configuration."""
        from starlette.responses import HTMLResponse

        if not self._user_has_edit_permission(request):
            await self._audit(
                request,
                success=False,
                event_type=AdminSecurityEventType.PERMISSION_DENIED,
                reason="permission_denied",
                route="save_widget_config",
            )
            return HTMLResponse("Permission denied", status_code=403)

        tenant_id = "default"
        user_id = "default"

        data = request.scope.get("admin_form_data")
        if data is None:
            data = await request.form()
        widget_name = data.get("widget_name")
        enabled = "enabled" in data
        params = {
            k.removeprefix("param_"): v
            for k, v in data.items()
            if k.startswith("param_")
        }

        prefs = (
            await self._settings_service.get_widget_prefs(tenant_id, user_id)
            if self._settings_service
            else {}
        )
        enabled_list = prefs.get("enabled", [])
        if enabled and widget_name not in enabled_list:
            enabled_list.append(widget_name)
        elif not enabled and widget_name in enabled_list:
            enabled_list.remove(widget_name)

        configs = prefs.get("configs", {})
        if params:
            configs[widget_name] = params
        elif widget_name in configs:
            del configs[widget_name]

        prefs["enabled"] = enabled_list
        prefs["configs"] = configs
        if self._settings_service:
            await self._settings_service.set_widget_prefs(tenant_id, user_id, prefs)
        await self._audit(
            request,
            widget_name=widget_name or "",
            kind="widget_config",
        )
        return HTMLResponse("", status_code=204)

    @post("/core/widgets/reorder")
    async def reorder_widgets(self, request: Request) -> object:
        """Save widget order after drag-and-drop."""
        from starlette.responses import HTMLResponse

        if not self._user_has_edit_permission(request):
            await self._audit(
                request,
                success=False,
                event_type=AdminSecurityEventType.PERMISSION_DENIED,
                reason="permission_denied",
                route="reorder_widgets",
            )
            return HTMLResponse("Permission denied", status_code=403)

        tenant_id = "default"
        user_id = "default"

        data = await request.json()
        order_list = data.get("order", [])
        prefs = (
            await self._settings_service.get_widget_prefs(tenant_id, user_id)
            if self._settings_service
            else {}
        )
        prefs["order"] = {name: idx for idx, name in enumerate(order_list)}
        if self._settings_service:
            await self._settings_service.set_widget_prefs(tenant_id, user_id, prefs)
        await self._audit(request, kind="widget_reorder")
        return HTMLResponse("", status_code=204)

    @get("/core/widgets/customize")
    async def customize_all_widgets(self, request: Request) -> object:
        """Render full dashboard customization panel with all widgets."""
        from starlette.responses import HTMLResponse

        tenant_id = "default"
        user_id = "default"

        prefs = (
            await self._settings_service.get_widget_prefs(tenant_id, user_id)
            if self._settings_service
            else {}
        )
        enabled_list = prefs.get("enabled", [])
        has_explicit_prefs = "enabled" in prefs

        grouped: dict[str, tuple[str, list[Any]]] = {}
        for contributor in self._registry.get_all():
            widgets = list(contributor.get_dashboard_widgets())
            if not widgets:
                continue
            toggles: list[Any] = []
            for wdef in widgets:
                name = wdef.name
                enabled = name in enabled_list
                if not has_explicit_prefs:
                    # No saved prefs yet — dashboard shows everything by default,
                    # so the form must render every widget as enabled.
                    enabled = True
                toggles.append(
                    el(
                        "label",
                        el(
                            "input",
                            type_="checkbox",
                            name=f"enabled_{name}",
                            value="1",
                            checked="checked" if enabled else None,
                        ),
                        el(
                            "span",
                            wdef.title,
                            class_="truncate text-sm font-medium",
                        ),
                        class_=(
                            "flex items-center gap-2 rounded-lg border border-border "
                            "bg-card px-3 py-2 cursor-pointer select-none "
                            "hover:bg-muted/50 transition-colors"
                        ),
                    )
                )
            label = getattr(contributor, "display_name", "") or contributor.name
            grouped[contributor.name] = (label, toggles)

        sections: list[Any] = []
        for label, toggles in grouped.values():
            sections.append(
                el(
                    "div",
                    el(
                        "h3",
                        label,
                        class_=(
                            "text-xs font-semibold uppercase tracking-wider "
                            "text-muted-foreground"
                        ),
                    ),
                    el("div", class_="mt-1.5 border-t border-border"),
                    el(
                        "div",
                        *toggles,
                        class_="mt-3 grid grid-cols-2 gap-2",
                    ),
                )
            )

        csrf_token = self._get_csrf_token(request)

        from lexigram.admin.ui.organisms.admin_slide_over import (
            render_slide_over_fragment,
        )

        form = el(
            "form",
            el("input", type_="hidden", name="csrf_token", value=csrf_token or ""),
            *sections,
            id="widget-customize-form",
            **{
                "hx-post": "/admin/core/widgets/customize/save",
                "hx-swap": "none",
                "hx-on:htmx:after-request": "if(event.detail.successful){window.location.reload();}",
            },
            class_="space-y-6",
        )

        return HTMLResponse(
            render_slide_over_fragment(
                title="Customize Dashboard",
                subtitle="Enable/disable widgets and configure their parameters.",
                content=form,
                size="xl",
                footer=[
                    el(
                        "button",
                        "Cancel",
                        type_="button",
                        **{"x-on:click": "open = false"},
                        class_="inline-flex items-center rounded-lg px-4 py-2 text-sm font-medium text-foreground bg-card border border-border hover:bg-muted transition-colors",
                    ),
                    el(
                        "button",
                        "Save All Changes",
                        type_="submit",
                        form="widget-customize-form",
                        class_="inline-flex items-center rounded-lg px-4 py-2 text-sm font-medium text-white bg-primary hover:bg-primary/90 transition-colors",
                    ),
                ],
            )
        )

    @post("/core/widgets/customize/save")
    async def save_all_widget_configs(self, request: Request) -> object:
        """Save all widget configurations from the customize panel."""
        from starlette.responses import HTMLResponse

        if not self._user_has_edit_permission(request):
            await self._audit(
                request,
                success=False,
                event_type=AdminSecurityEventType.PERMISSION_DENIED,
                reason="permission_denied",
                route="save_all_widget_configs",
            )
            return HTMLResponse("Permission denied", status_code=403)

        tenant_id = "default"
        user_id = "default"

        data = request.scope.get("admin_form_data")
        if data is None:
            data = await request.form()

        enabled_list: list[str] = []
        configs: dict[str, dict[str, str]] = {}
        all_widget_names: list[str] = []

        for contributor in self._registry.get_all():
            for wdef in contributor.get_dashboard_widgets():
                all_widget_names.append(wdef.name)

        for key, val in data.items():
            if key.startswith("enabled_"):
                wname = key.removeprefix("enabled_")
                if wname in all_widget_names and val:
                    enabled_list.append(wname)
            elif key.startswith("param__"):
                rest = key.removeprefix("param__")
                wname, pname = rest.split("__", 1)
                configs.setdefault(wname, {})[pname] = cast("str", val)

        existing = (
            await self._settings_service.get_widget_prefs(tenant_id, user_id)
            if self._settings_service
            else {}
        )
        prefs = {
            "enabled": enabled_list,
            "configs": configs,
            "order": existing.get("order", {}),
        }
        if self._settings_service:
            await self._settings_service.set_widget_prefs(tenant_id, user_id, prefs)
        await self._audit(
            request,
            kind="widget_customize",
            widget_count=len(all_widget_names),
        )
        return HTMLResponse("", status_code=204)


__all__ = ["WidgetController"]
