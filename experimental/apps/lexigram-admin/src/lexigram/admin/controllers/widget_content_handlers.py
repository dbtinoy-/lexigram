"""Handlers rendering dashboard widget and health-check fragments."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from starlette.requests import Request
from starlette.responses import HTMLResponse, Response

from lexigram.admin.dashboard.content_renderer import render_content
from lexigram.admin.params import parse_widget_params
from lexigram.contracts.admin.protocols import AdminContributorRegistryProtocol
from lexigram.contracts.admin.types import WidgetContent
from lexigram.logging import get_logger

logger = get_logger(__name__)


async def render_widget_fragment(
    request: Request,
    *,
    contributor_id: str,
    widget_name: str,
    registry: AdminContributorRegistryProtocol,
    settings_service: Any,
    resolver: Any,
    resolve_tenant: Callable[..., Awaitable[str]],
    has_permission: Callable[[Request, str | None], bool],
) -> object:
    """Render a widget fragment for the HTMX dashboard.

    Returns an inline error card when the widget is not found or fails
    to render, rather than returning an HTTP error status. This lets
    the dashboard grid maintain its layout even when individual widgets
    fail.
    """
    contributor = registry.get(contributor_id)
    if contributor is None:
        logger.warning(
            "widget_contributor_not_found",
            contributor_id=contributor_id,
            widget_name=widget_name,
        )
        return HTMLResponse(
            render_error_card(
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
    if widget_def is not None and not has_permission(request, widget_def.permission):
        return HTMLResponse(
            render_error_card(
                "You do not have permission to view this widget.",
                contributor_id=contributor_id,
                widget_name=widget_name,
            ),
            status_code=200,
        )

    params = parse_widget_params(dict(request.query_params))

    if settings_service:
        full_name = f"{contributor_id}.{widget_name}"
        tenant_id = await resolve_tenant(request, default="default")
        prefs = await settings_service.get_widget_prefs(tenant_id, "default")
        cfg = prefs.get("configs", {}).get(full_name, {})
        if "time_window_minutes" in cfg:
            from lexigram.contracts.admin.types import WidgetParams

            params = WidgetParams(
                page=params.page,
                page_size=params.page_size,
                time_window_minutes=int(cfg["time_window_minutes"]),
                raw=params.raw,
            )

    result = await contributor.render_widget(widget_name, params, resolver=resolver)

    if result.is_ok():
        vm = result.unwrap()
        return HTMLResponse(wrap_widget_body(vm.content, vm.title, vm.error))

    error = result.unwrap_err()
    logger.error(
        "widget_render_failed",
        contributor_id=contributor_id,
        widget_name=widget_name,
        error=str(error),
    )
    return HTMLResponse(
        render_error_card(
            str(error),
            contributor_id=contributor_id,
            widget_name=widget_name,
        ),
        status_code=200,
    )


async def render_health_check_fragment(
    request: Request,
    *,
    contributor_id: str,
    check_name: str,
    registry: AdminContributorRegistryProtocol,
    has_permission: Callable[[Request, str | None], bool],
) -> object:
    """Render a health check fragment for the HTMX dashboard."""
    contributor = registry.get(contributor_id)
    if contributor is None:
        return Response(
            content=f"Contributor '{contributor_id}' not found",
            status_code=404,
        )

    health_def = next(
        (
            h
            for h in contributor.get_health_definitions()
            if h.name == check_name or h.name == f"{contributor_id}.{check_name}"
        ),
        None,
    )
    if health_def is not None and not has_permission(request, health_def.permission):
        return Response(content="Permission denied", status_code=403)

    # Health URLs use the contributor-local suffix (for example,
    # /auth/health/token_store), while definitions and contributor handlers
    # conventionally use the canonical name (auth.token_store). Resolve the
    # canonical name before dispatch so the declared check actually runs.
    resolved_check_name = health_def.name if health_def is not None else check_name
    result = await contributor.render_health_check(resolved_check_name)

    if result.is_ok():
        return HTMLResponse(render_content(result.unwrap()))

    error = result.unwrap_err()
    return Response(content=str(error), status_code=422)


def wrap_widget_body(
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


def render_error_card(
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
