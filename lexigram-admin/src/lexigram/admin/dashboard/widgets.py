"""Admin dashboard widget types and infrastructure.

Provides WidgetType, WidgetConfig, DashboardConfig and supporting
store/registry infrastructure for admin dashboard assembly.
Widget definitions from lexigram-contracts are also re-exported here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol

from lexigram.admin.dashboard.page_filters import widget_fetch_url
from lexigram.contracts.admin.types import (
    DashboardWidgetDefinition,
    WidgetCategory,
    WidgetSize,
)
from lexigram.ui import el, render_to_string


def _render_live_widget_script() -> str:
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
    return (
        "<script>"
        "(function(){"
        "if(window.__lexigramLiveWidgets)return;"
        "window.__lexigramLiveWidgets=true;"
        "var es=new EventSource('/admin/_sse/widgets');"
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
        "})();"
        "</script>"
    )


class WidgetType(StrEnum):
    """Widget types for legacy dashboard builder."""

    METRIC = "metric"
    CHART = "chart"
    TABLE = "table"
    TEXT = "text"
    CUSTOM = "custom"
    STAT_CARD = "stat_card"
    ACTIVITY = "activity"
    HEALTH = "health"


@dataclass
class WidgetConfig:
    """Widget configuration."""

    id: str
    type: WidgetType
    title: str
    config: dict[str, Any] = field(default_factory=dict)
    position: dict[str, int] = field(
        default_factory=lambda: {"x": 0, "y": 0, "w": 1, "h": 1},
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "title": self.title,
            "config": self.config,
            "position": self.position,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WidgetConfig:
        """Deserialize from dictionary."""
        return cls(
            id=data["id"],
            type=WidgetType(data["type"]),
            title=data["title"],
            config=data.get("config", {}),
            position=data.get("position", {"x": 0, "y": 0, "w": 1, "h": 1}),
        )


@dataclass
class DashboardConfig:
    """Dashboard configuration."""

    id: str
    name: str
    widgets: list[WidgetConfig] = field(default_factory=list)
    layout: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "widgets": [w.to_dict() for w in self.widgets],
            "layout": self.layout,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DashboardConfig:
        """Deserialize from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            widgets=[WidgetConfig.from_dict(w) for w in data.get("widgets", [])],
            layout=data.get("layout", {}),
            created_at=datetime.fromisoformat(
                data.get("created_at", datetime.now().isoformat()),
            ),
            updated_at=datetime.fromisoformat(
                data.get("updated_at", datetime.now().isoformat()),
            ),
        )


class IWidget(Protocol):
    """Protocol for dashboard widgets."""

    async def render(self, config: dict[str, Any]) -> str:
        """Render widget HTML (async)."""
        ...

    def get_default_config(self) -> dict[str, Any]:
        """Get default widget configuration."""
        ...


class IDashboardStore(Protocol):
    """Protocol for dashboard persistence (async)."""

    async def save(self, dashboard: DashboardConfig) -> bool:
        """Save dashboard configuration."""
        ...

    async def load(self, dashboard_id: str) -> DashboardConfig | None:
        """Load dashboard configuration."""
        ...

    async def list(self) -> list[DashboardConfig]:
        """List all dashboards."""
        ...

    async def delete(self, dashboard_id: str) -> bool:
        """Delete dashboard."""
        ...


class InMemoryDashboardStore:
    """In-memory dashboard storage implementation."""

    def __init__(self) -> None:
        """Initialize store."""
        self.dashboards: dict[str, DashboardConfig] = {}

    async def save(self, dashboard: DashboardConfig) -> bool:
        """Save dashboard."""
        dashboard.updated_at = datetime.now()
        self.dashboards[dashboard.id] = dashboard
        return True

    async def load(self, dashboard_id: str) -> DashboardConfig | None:
        """Load dashboard."""
        return self.dashboards.get(dashboard_id)

    async def list(self) -> list[DashboardConfig]:
        """List all dashboards."""
        return list(self.dashboards.values())

    async def delete(self, dashboard_id: str) -> bool:
        """Delete dashboard."""
        if dashboard_id in self.dashboards:
            del self.dashboards[dashboard_id]
            return True
        return False


class WidgetRegistry:
    """Registry for dashboard widget implementations."""

    def __init__(self) -> None:
        """Initialize registry."""
        self._widgets: dict[str, type[IWidget]] = {}

    def register(self, widget_type: str, widget_class: type[IWidget]) -> None:
        """Register widget type."""
        self._widgets[widget_type] = widget_class

    def get(self, widget_type: str) -> type[IWidget] | None:
        """Get widget class by type."""
        return self._widgets.get(widget_type)

    def list_types(self) -> list[str]:
        """List registered widget types."""
        return list(self._widgets.keys())

    def create_widget(self, widget_type: str) -> IWidget | None:
        """Create widget instance."""
        widget_class = self.get(widget_type)
        if widget_class:
            return widget_class()
        return None

    def render_contributor_widgets(
        self,
        contributor_widgets: list[DashboardWidgetDefinition],
        width: str = "100%",
        page_filters: dict[str, Any] | None = None,
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
            widget_class = self.get(lookup_key) or self.get(widget_def.name)

            # Build common HTMX trigger: load on page render, plus optional polling.
            # Initial loads are staggered so the dashboard does not fire every
            # widget request at once — that would saturate the browser's HTTP/1.1
            # connection pool (~6 per origin) and starve sidebar navigation
            # requests for the whole drain.
            load_trigger = f"load delay:{widget_index * 350}ms"
            if refresh_trigger:
                load_trigger = f"{load_trigger}, {refresh_trigger}"
            if is_live:
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

            cog = el(
                "button",
                "⚙",
                **{
                    "hx-get": f"/admin/core/widgets/{widget_def.name}/config",
                    "hx-target": "#slide-over-container",
                    "hx-swap": "innerHTML",
                    "hx-push-url": "false",
                },
                class_="opacity-0 group-hover:opacity-100 transition-opacity ml-auto text-muted-foreground hover:text-muted-foreground text-sm cursor-pointer",
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

            # Loading skeleton shown while HTMX request is in flight
            skeleton = el(
                "div",
                el("div", class_="h-4 bg-muted rounded w-3/4 mb-2"),
                el("div", class_="h-4 bg-muted rounded w-1/2 mb-2"),
                el("div", class_="h-4 bg-muted rounded w-5/6"),
                class_="animate-pulse py-2",
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

            body_kwargs: dict[str, Any] = {
                "class": "widget-body",
                "id": f"widget-{widget_def.name}-body",
                "hx-get": widget_fetch_url(widget_def.render_endpoint, page_filters),
                "hx-trigger": load_trigger,
                "hx-swap": "innerHTML",
            }
            if is_live:
                body_kwargs["data-live-resources"] = ",".join(
                    widget_def.live_resource_types
                )
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

            parts.append(render_to_string(card))

        if any(w.live_resource_types for w in contributor_widgets):
            parts.append(_render_live_widget_script())

        return "".join(parts)


def render_dashboard_widgets(
    definitions: list[DashboardWidgetDefinition],
    registry: WidgetRegistry,
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
    return registry.render_contributor_widgets(definitions)


from lexigram.admin.dashboard.widget_types import ConfigField


def render_widget_config_popup(
    widget_name: str,
    title: str,
    fields: list[ConfigField],
    current_values: dict[str, Any],
    enabled: bool = True,
) -> str:
    """Render HTML for a widget config dialog."""
    rows: list[Any] = [
        el(
            "label",
            el(
                "input",
                type_="checkbox",
                name="enabled",
                checked="checked" if enabled else None,
            ),
            " Show on dashboard",
            class_="flex items-center gap-2 text-sm mb-4",
        )
    ]

    for f in fields:
        if isinstance(f, dict):
            f = ConfigField(**f)
        value = current_values.get(f.name, f.default)
        rows.append(
            el(
                "div",
                el("label", f.label, class_="block text-sm font-medium mb-1"),
                _render_field_input(f, value),
                class_="mb-3",
            ),
        )

    from lexigram.admin.ui.organisms.admin_slide_over import (
        render_slide_over_fragment,
    )

    form = el(
        "form",
        *rows,
        el("input", type_="hidden", name="widget_name", value=widget_name),
        id=f"widget-config-form-{widget_name}",
        **{
            "hx-post": "/admin/core/widgets/config",
            "hx-swap": "none",
            "hx-on:htmx:after-request": "if(event.detail.successful){window.location.reload();}",
        },
        class_="space-y-3",
    )

    return render_slide_over_fragment(
        title=f"Configure: {title}",
        subtitle="Update this widget's settings.",
        content=form,
        size="md",
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
                "Save",
                type_="submit",
                form=f"widget-config-form-{widget_name}",
                class_="inline-flex items-center rounded-lg px-4 py-2 text-sm font-medium text-white bg-primary hover:bg-primary/90 transition-colors",
            ),
        ],
    )


def _render_field_input(
    field: ConfigField, current: Any, widget_name: str | None = None
) -> str:
    prefix = f"param__{widget_name}__" if widget_name else "param_"
    if field.type == "select" and field.options:
        opts = [
            el(
                "option",
                label,
                value=str(val),
                selected="selected" if val == current else None,
            )
            for val, label in field.options
        ]
        return str(
            el(
                "select",
                *opts,
                name=f"{prefix}{field.name}",
                class_="w-full border rounded px-2 py-1 text-sm",
            )
        )
    if field.type == "number":
        return str(
            el(
                "input",
                type_="number",
                name=f"{prefix}{field.name}",
                value=str(current) if current is not None else "",
                class_="w-full border rounded px-2 py-1 text-sm",
            )
        )
    if field.type == "boolean":
        return str(
            el(
                "input",
                type_="checkbox",
                name=f"{prefix}{field.name}",
                checked="checked" if current else None,
            )
        )
    return str(
        el(
            "input",
            type_="text",
            name=f"{prefix}{field.name}",
            value=str(current) if current is not None else "",
            class_="w-full border rounded px-2 py-1 text-sm",
        )
    )


__all__ = [
    "ConfigField",
    "DashboardConfig",
    "DashboardWidgetDefinition",
    "IDashboardStore",
    "IWidget",
    "InMemoryDashboardStore",
    "WidgetCategory",
    "WidgetConfig",
    "WidgetRegistry",
    "WidgetSize",
    "WidgetType",
    "render_dashboard_widgets",
    "render_widget_config_popup",
]
