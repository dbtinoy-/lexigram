"""Handlers for per-widget configuration preferences (popup, save, reorder)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from starlette.requests import Request
from starlette.responses import HTMLResponse

from lexigram.admin.dashboard.widget_types import ConfigField
from lexigram.contracts.admin.protocols import AdminContributorRegistryProtocol


async def render_config_popup(
    request: Request,
    *,
    name: str,
    registry: AdminContributorRegistryProtocol,
    settings_service: Any,
    resolve_tenant: Callable[..., Awaitable[str]],
    user_has_edit_permission: Callable[[Request], bool],
    audit: Callable[..., Awaitable[None]],
) -> object:
    """Render config popup for a widget."""
    from lexigram.admin.controllers.widget_handler_support import ensure_edit_allowed
    from lexigram.admin.dashboard.widgets import render_widget_config_popup

    tenant_id = await resolve_tenant(request, default="default")
    user_id = "default"

    widget_def = None
    contributor = None
    for c in registry.get_all():
        for wdef in c.get_dashboard_widgets():
            if wdef.name == name:
                widget_def = wdef
                contributor = c
                break
        if widget_def:
            break

    if widget_def is None:
        return HTMLResponse("Widget not found", status_code=404)

    denied = await ensure_edit_allowed(
        user_has_edit_permission, audit, request, "widget_config_popup"
    )
    if denied is not None:
        return denied

    schema: list[ConfigField] = getattr(
        contributor, "get_widget_config_schema", lambda _: []
    )(name)

    prefs = (
        await settings_service.get_widget_prefs(tenant_id, user_id)
        if settings_service
        else {}
    )
    enabled = "enabled" not in prefs or name in prefs.get("enabled", [])
    cfg = prefs.get("configs", {}).get(name, {})

    html = render_widget_config_popup(name, widget_def.title, schema, cfg, enabled)
    return HTMLResponse(html)


async def save_config(
    request: Request,
    *,
    settings_service: Any,
    resolve_tenant: Callable[..., Awaitable[str]],
    user_has_edit_permission: Callable[[Request], bool],
    audit: Callable[..., Awaitable[None]],
) -> object:
    """Save a single widget's configuration."""
    from lexigram.admin.controllers.widget_handler_support import ensure_edit_allowed

    denied = await ensure_edit_allowed(
        user_has_edit_permission, audit, request, "save_widget_config"
    )
    if denied is not None:
        return denied

    tenant_id = await resolve_tenant(request, default="default")
    user_id = "default"

    data = request.scope.get("admin_form_data")
    if data is None:
        data = await request.form()
    widget_name = data.get("widget_name")
    enabled = "enabled" in data
    params = {
        k.removeprefix("param_"): v for k, v in data.items() if k.startswith("param_")
    }

    prefs = (
        await settings_service.get_widget_prefs(tenant_id, user_id)
        if settings_service
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
    if settings_service:
        await settings_service.set_widget_prefs(tenant_id, user_id, prefs)
    await audit(
        request,
        widget_name=widget_name or "",
        kind="widget_config",
    )
    return HTMLResponse("", status_code=204)


async def reorder(
    request: Request,
    *,
    settings_service: Any,
    resolve_tenant: Callable[..., Awaitable[str]],
    user_has_edit_permission: Callable[[Request], bool],
    audit: Callable[..., Awaitable[None]],
) -> object:
    """Save widget order after drag-and-drop."""
    from lexigram.admin.controllers.widget_handler_support import ensure_edit_allowed

    denied = await ensure_edit_allowed(
        user_has_edit_permission, audit, request, "reorder_widgets"
    )
    if denied is not None:
        return denied

    tenant_id = await resolve_tenant(request, default="default")
    user_id = "default"

    data = await request.json()
    order_list = data.get("order", [])
    prefs = (
        await settings_service.get_widget_prefs(tenant_id, user_id)
        if settings_service
        else {}
    )
    prefs["order"] = {name: idx for idx, name in enumerate(order_list)}
    if settings_service:
        await settings_service.set_widget_prefs(tenant_id, user_id, prefs)
    await audit(request, kind="widget_reorder")
    return HTMLResponse("", status_code=204)
