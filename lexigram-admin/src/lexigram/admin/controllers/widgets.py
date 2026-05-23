"""Widget controller — routes HTMX widget requests to contributors."""

from __future__ import annotations

import inspect
from typing import Any, cast

from starlette.requests import Request
from starlette.routing import Route

from lexigram.admin.auth.protocols import AdminAuditLogServiceProtocol
from lexigram.admin.auth.types import AdminSecurityEventType
from lexigram.admin.dashboard.widget_types import ConfigField
from lexigram.admin.params import parse_widget_params
from lexigram.contracts.admin.protocols import AdminContributorRegistryProtocol
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
    ) -> None:
        self._registry = registry
        self._settings_service: Any = None
        self._resolver: Any = None
        self._audit_service = audit_service

    # -- helpers --

    def _user_has_edit_permission(self, request: Request) -> bool:
        """Check whether the requesting user may mutate widget prefs."""
        user = getattr(getattr(request, "state", None), "user", None)
        permissions = frozenset(getattr(user, "permissions", None) or ())
        return permissions.issuperset(_REQUIRED_PERMISSIONS)

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
            return HTMLResponse(self._wrap_widget_body(vm.body, vm.title, vm.error))

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
        body: str,
        title: str | None = None,
        error: str | None = None,
    ) -> str:
        """Wrap widget body in a container with optional error banner."""
        from lexigram.ui.core.base import el, render_to_string

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
        children.append(el("div", body, class_="widget-content"))
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

        result = await contributor.render_health_check(check_name)

        if result.is_ok():
            return HTMLResponse(result.unwrap())

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
        enabled = name in prefs.get("enabled", [])
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

        from lexigram.admin.dashboard.widgets import _render_field_input

        tenant_id = "default"
        user_id = "default"

        prefs = (
            await self._settings_service.get_widget_prefs(tenant_id, user_id)
            if self._settings_service
            else {}
        )
        enabled_list = prefs.get("enabled", [])
        configs = prefs.get("configs", {})

        rows: list[Any] = [
            el("h3", "Customize Dashboard", class_="text-xl font-semibold mb-4"),
            el(
                "p",
                "Enable/disable widgets and configure their parameters.",
                class_="text-sm text-muted-foreground mb-6",
            ),
        ]

        for contributor in self._registry.get_all():
            for wdef in contributor.get_dashboard_widgets():
                name = wdef.name
                enabled = name in enabled_list
                schema: list[ConfigField] = getattr(
                    contributor, "get_widget_config_schema", lambda _: []
                )(name)
                cfg = configs.get(name, {})

                from lexigram.admin.dashboard.widget_types import ConfigField

                field_inputs: list[Any] = []
                for f in schema:
                    if isinstance(f, dict):
                        f = ConfigField(**f)
                    value = cfg.get(f.name, f.default)
                    field_inputs.append(
                        el(
                            "div",
                            el(
                                "label",
                                f.label,
                                class_="block text-xs font-medium mb-1",
                            ),
                            _render_field_input(f, value, widget_name=name),
                            class_="mb-2",
                        ),
                    )

                widget_row = el(
                    "div",
                    el(
                        "label",
                        el(
                            "input",
                            type_="checkbox",
                            name=f"enabled_{name}",
                            value="1",
                            checked="checked" if enabled else None,
                        ),
                        el("span", wdef.title, class_="font-medium ml-2"),
                        el(
                            "span",
                            f" ({wdef.contributor})",
                            class_="text-xs text-muted-foreground ml-1",
                        ),
                        class_="flex items-center mb-2",
                    ),
                    el("div", *field_inputs, class_="ml-6"),
                    class_="mb-4 pb-4 border-b border-border last:border-0",
                )
                rows.append(widget_row)

        form = el(
            "form",
            *rows,
            el(
                "div",
                el(
                    "button",
                    "Save All Changes",
                    type_="submit",
                    class_="bg-primary text-primary-foreground px-4 py-2 rounded hover:bg-primary/90",
                ),
                el(
                    "button",
                    "Cancel",
                    type_="button",
                    class_="ml-2 text-muted-foreground px-4 py-2 rounded hover:bg-muted",
                    onclick="this.closest('dialog').close()",
                ),
                class_="mt-6 flex justify-end gap-2 sticky bottom-0 bg-card py-3 border-t",
            ),
            **{
                "hx-post": "/admin/core/widgets/customize/save",
                "hx-swap": "none",
                "hx-on:htmx:afterRequest": "document.getElementById('widget-config-dialog').close()",
            },
            class_="p-6 max-h-[80vh] overflow-y-auto",
        )

        return HTMLResponse(str(form))

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
