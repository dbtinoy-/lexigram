"""Handlers for the full dashboard customization panel."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, cast

from starlette.requests import Request
from starlette.responses import HTMLResponse

from lexigram.contracts.admin.protocols import AdminContributorRegistryProtocol
from lexigram.ui import el


async def render_customize_panel(
    request: Request,
    *,
    registry: AdminContributorRegistryProtocol,
    settings_service: Any,
    resolve_tenant: Callable[..., Awaitable[str]],
    csrf_token: str | None,
    user_has_edit_permission: Callable[[Request], bool],
    audit: Callable[..., Awaitable[None]],
) -> object:
    """Render full dashboard customization panel with all widgets."""
    from lexigram.admin.controllers.widget_handler_support import ensure_edit_allowed
    from lexigram.admin.resources.urls import admin_prefix_from_request

    denied = await ensure_edit_allowed(
        user_has_edit_permission, audit, request, "customize_all_widgets"
    )
    if denied is not None:
        return denied

    tenant_id = await resolve_tenant(request, default="default")
    user_id = "default"

    prefs = (
        await settings_service.get_widget_prefs(tenant_id, user_id)
        if settings_service
        else {}
    )
    enabled_list = prefs.get("enabled", [])
    has_explicit_prefs = "enabled" in prefs

    grouped: dict[str, tuple[str, list[Any]]] = {}
    for contributor in registry.get_all():
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

    from lexigram.admin.ui.organisms.admin_slide_over import (
        render_slide_over_fragment,
    )

    customize_save_url = (
        admin_prefix_from_request(request).rstrip("/") or "/admin"
    ) + "/core/widgets/customize/save"
    form = el(
        "form",
        el("input", type_="hidden", name="csrf_token", value=csrf_token or ""),
        *sections,
        id="widget-customize-form",
        **{
            "hx-post": customize_save_url,
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


async def save_all_configs(
    request: Request,
    *,
    registry: AdminContributorRegistryProtocol,
    settings_service: Any,
    resolve_tenant: Callable[..., Awaitable[str]],
    user_has_edit_permission: Callable[[Request], bool],
    audit: Callable[..., Awaitable[None]],
) -> object:
    """Save all widget configurations from the customize panel."""
    from lexigram.admin.controllers.widget_handler_support import ensure_edit_allowed

    denied = await ensure_edit_allowed(
        user_has_edit_permission, audit, request, "save_all_widget_configs"
    )
    if denied is not None:
        return denied

    tenant_id = await resolve_tenant(request, default="default")
    user_id = "default"

    data = request.scope.get("admin_form_data")
    if data is None:
        data = await request.form()

    enabled_list: list[str] = []
    configs: dict[str, dict[str, str]] = {}
    all_widget_names: list[str] = []

    for contributor in registry.get_all():
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
        await settings_service.get_widget_prefs(tenant_id, user_id)
        if settings_service
        else {}
    )
    prefs = {
        "enabled": enabled_list,
        "configs": configs,
        "order": existing.get("order", {}),
    }
    if settings_service:
        await settings_service.set_widget_prefs(tenant_id, user_id, prefs)
    await audit(
        request,
        kind="widget_customize",
        widget_count=len(all_widget_names),
    )
    return HTMLResponse("", status_code=204)
