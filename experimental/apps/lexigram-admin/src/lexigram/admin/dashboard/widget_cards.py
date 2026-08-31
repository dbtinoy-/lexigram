"""Admin dashboard contributor widget card rendering infrastructure.

Hosts :class:`WidgetRegistry` — the lookup table for ``IWidget``
implementations — and the HTML rendering of contributor-supplied
``DashboardWidgetDefinition`` cards, including the shared EventSource
script that drives live (SSE-pushed) widgets.
"""

from __future__ import annotations

from typing import Any

from lexigram.admin.dashboard.page_filters import widget_fetch_url
from lexigram.admin.dashboard.widget_defs import IWidget
from lexigram.contracts.admin.types import (
    DashboardWidgetDefinition,
    WidgetSize,
)
from lexigram.primitives.registry import Registry
from lexigram.ui import el, render_to_string


def _admin_endpoint(path: str, admin_prefix: str) -> str:
    """Normalize a widget endpoint to the active admin mount."""
    normalized = path if path.startswith("/") else f"/{path}"
    prefix = (admin_prefix or "/admin").rstrip("/") or "/admin"
    if normalized == prefix or normalized.startswith(f"{prefix}/"):
        return normalized
    if normalized == "/admin" or normalized.startswith("/admin/"):
        return f"{prefix}{normalized[len('/admin') :]}"
    return normalized


def _render_live_widget_script(admin_prefix: str = "/admin") -> str:
    """Shared EventSource connection driving all live widgets on the page.

    One connection per page, not one per widget — browsers cap concurrent
    HTTP/1.1 connections per origin (~6), the same constraint the staggered
    hx-trigger delays above already work around. Each live widget's body
    element carries data-live-resources (comma-separated resource types,
    or "*" for broadcast-only widgets like activity); on a matching SSE
    message this re-triggers that widget's existing htmx load (reconcile
    via the same snapshot endpoint the widget already renders from — no
    separate patch/diff wire format).
    """
    prefix = (admin_prefix or "/admin").rstrip("/") or "/admin"
    return (
        "<script>"
        "(function(){"
        # Reuse a live connection, but treat a closed/errored one as absent so
        # the stream is re-established after an SPA body swap. A plain boolean
        # guard would leave every page after the first with no live updates.
        "var existing=window.__lexigramLiveWidgets;"
        "if(existing&&existing.readyState!==2)return;"
        f"var es=new EventSource('{prefix}/_sse/widgets');"
        "window.__lexigramLiveWidgets=es;"
        "es.onmessage=function(ev){"
        "var data;"
        "try{data=JSON.parse(ev.data);}catch(e){return;}"
        "var resourceType=(data.data||{}).resource_type;"
        "document.querySelectorAll('[data-live-resources]').forEach(function(el){"
        "var types=el.getAttribute('data-live-resources').split(',');"
        "if(types.indexOf('*')!==-1||(resourceType&&types.indexOf(resourceType)!==-1)){"
        "htmx.trigger(el,'live-refresh');"
        "}"
        "});"
        "};"
        # Drop the handle on error so the guard above can reconnect. The
        # browser retries on its own; clearing the reference only matters
        # once it gives up and the connection is permanently closed.
        "es.onerror=function(){"
        "if(es.readyState===2&&window.__lexigramLiveWidgets===es){"
        "window.__lexigramLiveWidgets=null;"
        "}"
        "};"
        # Close on unload so the stream does not hold a connection slot.
        "window.addEventListener('pagehide',function(){"
        "if(window.__lexigramLiveWidgets===es){window.__lexigramLiveWidgets=null;}"
        "es.close();"
        "});"
        "})();"
        "</script>"
    )


def _render_widget_state_script() -> str:
    """Per-widget load/error state, delegated from the document root.

    HTMX does not swap non-2xx responses, so a widget whose endpoint fails
    would otherwise keep showing its loading skeleton indefinitely — visually
    identical to a slow request, with no way to tell that it had failed or to
    retry it. This resolves each widget's busy state and renders a scoped
    error with a retry button in the card that failed, leaving the rest of
    the dashboard usable.

    One delegated listener serves every widget rather than inline handlers
    per card, so the cost does not grow with dashboard size.
    """
    return (
        "<script>"
        "(function(){"
        "if(window.__lexigramWidgetState)return;"
        "window.__lexigramWidgetState=true;"
        "function body(elt){"
        "return elt&&elt.closest?elt.closest('[data-widget-body]'):null;"
        "}"
        "document.body.addEventListener('htmx:beforeRequest',function(e){"
        "var b=body(e.detail&&e.detail.elt);"
        "if(b)b.setAttribute('aria-busy','true');"
        "});"
        "document.body.addEventListener('htmx:afterSwap',function(e){"
        "var b=body(e.detail&&e.detail.target);"
        "if(b)b.setAttribute('aria-busy','false');"
        "});"
        # Both a non-2xx response and a transport failure leave the widget
        # unswapped; treat them the same from the user's point of view.
        "function fail(e){"
        "var b=body(e.detail&&e.detail.elt);"
        "if(!b)return;"
        "b.setAttribute('aria-busy','false');"
        "var title=b.getAttribute('data-widget-title')||'This widget';"
        "var xhr=e.detail&&e.detail.xhr;"
        "var status=xhr&&xhr.status?xhr.status:0;"
        "var reason=status===403?'You do not have access to this data.'"
        ":status===404?'This widget is no longer available.'"
        ":status>=500?'The server could not load this widget.'"
        ":status===0?'Could not reach the server.'"
        ":'This widget could not be loaded.';"
        "while(b.firstChild)b.removeChild(b.firstChild);"
        "var wrap=document.createElement('div');"
        "wrap.className='py-3 text-sm';"
        "wrap.setAttribute('role','alert');"
        "var msg=document.createElement('p');"
        "msg.className='text-muted-foreground';"
        "msg.textContent=reason;"
        "var btn=document.createElement('button');"
        "btn.type='button';"
        "btn.className='mt-2 inline-flex items-center rounded border "
        "border-border px-2 py-1 text-xs font-medium text-foreground "
        "hover:bg-muted focus-visible:outline-none focus-visible:ring-2 "
        "focus-visible:ring-ring';"
        "btn.textContent='Retry';"
        "btn.setAttribute('aria-label','Retry loading '+title);"
        "btn.addEventListener('click',function(){"
        "if(window.htmx)window.htmx.trigger(b,'live-refresh');"
        "});"
        "wrap.appendChild(msg);"
        "wrap.appendChild(btn);"
        "b.appendChild(wrap);"
        "}"
        "document.body.addEventListener('htmx:responseError',fail);"
        "document.body.addEventListener('htmx:sendError',fail);"
        "document.body.addEventListener('htmx:timeout',fail);"
        "})();"
        "</script>"
    )


class WidgetRegistry(Registry[str, type[IWidget]]):
    """Registry for dashboard widget implementations.

    Widget implementations are contributed by applications (no built-in
    set), so instances start empty and are populated via ``register()`` —
    the core registry's plugin pattern.
    """

    def __init__(self) -> None:
        """Initialize an empty widget registry."""
        super().__init__(name="admin.dashboard.widgets", allow_overwrite=True)

    def list_types(self) -> list[str]:
        """List registered widget types."""
        return sorted(self.keys())

    def create_widget(self, widget_type: str) -> IWidget | None:
        """Create widget instance for *widget_type*, or None when unknown."""
        widget_class = self.get(widget_type)
        if widget_class:
            return widget_class()
        return None

    def render_contributor_widgets(
        self,
        contributor_widgets: list[DashboardWidgetDefinition],
        width: str = "100%",
        page_filters: dict[str, Any] | None = None,
        admin_prefix: str = "/admin",
    ) -> str:
        """Render HTML for all contributor-supplied ``DashboardWidgetDefinition`` items.

        For each widget definition the registry is consulted using the widget's
        ``name`` as the lookup key.  If a matching ``IWidget`` class is found,
        a rich card is rendered that loads its content via an HTMX ``hx-get``
        request to the definition's ``render_endpoint``.  When no match is
        found a lightweight ``<div class="widget-placeholder">`` card is
        rendered instead so contributors can always see their widget slot.

        Widget sizing from ``DashboardWidgetDefinition.size`` maps to CSS
        grid column spans (SMALL=1, MEDIUM=2, LARGE=3, FULL=4).  If
        ``refresh_interval_seconds`` is set, the card body auto-refreshes
        via ``hx-trigger="every <N>ms"``.

        Args:
            contributor_widgets: Widget definitions supplied by contributors.
            width: CSS ``width`` value applied to each card wrapper.
            page_filters: Optional page-level filter values appended as query
                parameters to every widget's fetch URL, so widget render
                endpoints can react to the page's filter state.

        Returns:
            Concatenated HTML string for all widget cards.
        """
        if not contributor_widgets:
            return render_to_string(
                el(
                    "div",
                    el(
                        "div",
                        class_="text-muted-foreground text-lg mb-1",
                    ),
                    el(
                        "p",
                        "No contributor widgets configured.",
                        class_="text-sm text-muted-foreground",
                    ),
                    class_="widget-empty-state bg-muted border border-border rounded-lg p-6 text-center",
                )
            )

        parts: list[str] = []
        for widget_index, widget_def in enumerate(contributor_widgets):
            parts.append(
                _render_contributor_card(
                    self,
                    widget_index,
                    widget_def,
                    width=width,
                    page_filters=page_filters,
                    admin_prefix=admin_prefix,
                )
            )

        parts.append(_render_widget_state_script())

        if any(w.live_resource_types for w in contributor_widgets):
            parts.append(_render_live_widget_script(admin_prefix))

        return "".join(parts)


def _render_contributor_card(
    registry: WidgetRegistry,
    widget_index: int,
    widget_def: DashboardWidgetDefinition,
    width: str,
    page_filters: dict[str, Any] | None,
    admin_prefix: str,
) -> str:
    """Render a single contributor widget card as HTML."""
    # Map widget size to grid column span
    size_col_map = {
        WidgetSize.SMALL: "",
        WidgetSize.MEDIUM: "lg:col-span-2",
        WidgetSize.LARGE: "lg:col-span-3",
        WidgetSize.FULL: "lg:col-span-4",
    }
    col_span = size_col_map.get(widget_def.size, "")

    # Build refresh trigger if interval is set. Live widgets (declared
    # via live_resource_types) are pushed to via a shared EventSource
    # instead of polled — see the script emitted after this loop.
    is_live = bool(widget_def.live_resource_types)
    refresh_trigger = ""
    if (
        not is_live
        and widget_def.refresh_interval_seconds
        and widget_def.refresh_interval_seconds > 0
    ):
        interval_ms = widget_def.refresh_interval_seconds * 1000
        refresh_trigger = f"every {interval_ms}ms"

    # Resolve a matching IWidget class from the registry.
    # Primary key is the definition name; fall back to category value.
    lookup_key = getattr(widget_def, "widget_type", widget_def.name)
    widget_class = registry.get(lookup_key) or registry.get(widget_def.name)

    # Build common HTMX trigger: load on page render, plus optional polling.
    # Initial loads are staggered so the dashboard does not fire every
    # widget request at once — that would saturate the browser's HTTP/1.1
    # connection pool (~6 per origin) and starve sidebar navigation
    # requests for the whole drain.
    load_trigger = f"load delay:{widget_index * 350}ms"
    if refresh_trigger:
        load_trigger = f"{load_trigger}, {refresh_trigger}"
    # Every widget listens for live-refresh, not just SSE-driven ones: the
    # retry button after a failure re-fires the request through this same
    # trigger, and a widget that failed to load is exactly the one that
    # needs to be retryable.
    load_trigger = f"{load_trigger}, live-refresh"

    # Build the title bar with optional icon and config cog.
    icon_html = (
        el("span", widget_def.icon, class_="widget-icon mr-1")
        if widget_def.icon
        else None
    )
    title_children: list[Any] = []
    if icon_html is not None:
        title_children.append(icon_html)
    title_children.append(widget_def.title)

    config_endpoint = _admin_endpoint(
        f"/admin/core/widgets/{widget_def.name}/config", admin_prefix
    )
    # The control is revealed on hover, but hover is not the only way in:
    # focus-within reveals it for keyboard users and it stays operable for
    # screen readers, which an opacity-only rule would hide from sighted
    # keyboard navigation without ever removing it from the tab order.
    cog = el(
        "button",
        el("span", "⚙", **{"aria-hidden": "true"}),
        el("span", f"Configure {widget_def.title} widget", class_="sr-only"),
        **{
            "hx-get": config_endpoint,
            "hx-target": "#slide-over-container",
            "hx-swap": "innerHTML",
            "hx-push-url": "false",
            "aria-label": f"Configure {widget_def.title} widget",
            "aria-haspopup": "dialog",
        },
        type="button",
        class_=(
            "opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 "
            "focus-visible:opacity-100 transition-opacity ml-auto rounded "
            "text-muted-foreground hover:text-foreground text-sm cursor-pointer "
            "focus-visible:outline-none focus-visible:ring-2 "
            "focus-visible:ring-ring focus-visible:ring-offset-1"
        ),
    )
    title_row = el(
        "div",
        *title_children,
        cog,
        class_="widget-title text-sm font-semibold text-foreground mb-2 flex items-center",
    )

    # Contributor label and description
    subtitle_parts: list[str] = []
    if widget_def.contributor:
        subtitle_parts.append(widget_def.contributor)
    if widget_def.description:
        subtitle_parts.append(widget_def.description)

    # Loading skeleton shown while the HTMX request is in flight. The bars
    # are decorative, so they are hidden from assistive tech and replaced by
    # a single spoken "Loading" message rather than three anonymous boxes.
    skeleton = el(
        "div",
        el(
            "div",
            el("div", class_="h-4 bg-muted rounded w-3/4 mb-2"),
            el("div", class_="h-4 bg-muted rounded w-1/2 mb-2"),
            el("div", class_="h-4 bg-muted rounded w-5/6"),
            class_="animate-pulse py-2 motion-reduce:animate-none",
            **{"aria-hidden": "true"},
        ),
        el("span", f"Loading {widget_def.title}…", class_="sr-only"),
        class_="widget-skeleton",
    )

    card_children: list[Any] = [
        title_row,
    ]

    if subtitle_parts:
        card_children.append(
            el(
                "div",
                " · ".join(subtitle_parts),
                class_="text-xs text-muted-foreground mb-3",
            ),
        )

    # HTMX does not swap non-2xx responses by default, so without this the
    # skeleton would pulse forever on a failed widget and look like a hang
    # rather than an error. Errors are surfaced in the card itself, next to
    # the widget that failed, with a retry that re-fires the same request.
    body_kwargs: dict[str, Any] = {
        "class": "widget-body",
        "id": f"widget-{widget_def.name}-body",
        "hx-get": widget_fetch_url(
            _admin_endpoint(widget_def.render_endpoint, admin_prefix), page_filters
        ),
        "hx-trigger": load_trigger,
        "hx-swap": "innerHTML",
        "aria-busy": "true",
        "aria-live": "polite",
        "data-widget-body": widget_def.name,
        "data-widget-title": widget_def.title,
    }
    if is_live:
        body_kwargs["data-live-resources"] = ",".join(widget_def.live_resource_types)
    card_children.append(
        el(
            "div",
            skeleton,
            **body_kwargs,
        ),
    )

    card = el(
        "div",
        *card_children,
        id=f"widget-card-{widget_def.name}",
        data_widget_name=widget_def.name,
        class_=f"widget-card bg-card border border-border rounded-lg shadow p-4 group {col_span}".strip(),
        style=f"width:{width};",
    )

    return render_to_string(card)


def render_dashboard_widgets(
    definitions: list[DashboardWidgetDefinition],
    registry: WidgetRegistry,
    *,
    admin_prefix: str = "/admin",
) -> str:
    """Render all dashboard widget definitions using the provided registry.

    Convenience wrapper around :meth:`WidgetRegistry.render_contributor_widgets`
    for callers that already hold a ``WidgetRegistry`` instance and a list of
    ``DashboardWidgetDefinition`` objects.

    Args:
        definitions: Widget definitions to render.
        registry: Widget registry to look up implementations.

    Returns:
        Concatenated HTML string for all widget cards.
    """
    return registry.render_contributor_widgets(definitions, admin_prefix=admin_prefix)


__all__ = ["WidgetRegistry", "render_dashboard_widgets"]
