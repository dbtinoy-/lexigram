from __future__ import annotations

from typing import Any

from lexigram.admin.ui.molecules.filter_bar import FilterBar
from lexigram.admin.ui.organisms.data_table.view_controls import (
    DATA_VIEW_OPTIONS,
    controls_for,
)
from lexigram.ui import (
    ActionButton,
    ColumnVisibilitySwitcher,
    Component,
    DensitySwitcher,
    GroupBySwitcher,
    LayoutSwitcher,
    SearchBar,
    SortSwitcher,
    ViewSwitcher,
    Zones,
    el,
)


class TableToolbar(Component):
    """
    Handles the top area of the DataTable: Actions, Switchers, Search, Filters.
    """

    def __init__(self, config: Any, state: Any, user: Any = None):
        self.config = config
        self.state = state
        self.user = user

    def render(self) -> Any:
        return el(
            "div",
            self.render_header(),
            self.render_search(),
            self.render_filters(),
        )

    def render_header(self, bulk_actions: list[Any] | None = None) -> Any:
        # 1. Header Actions (Create New, etc.) - Always visible but grouped with Bulk
        header_buttons = []
        for action in self.config.header_actions:
            if not action.is_visible(self.user):
                continue

            # Old-style (lexigram.ui) header action: inject default create URL
            # and render via the shared old/new action bridge.
            from lexigram.ui import Action as OldActionBase

            if isinstance(action, OldActionBase) and not hasattr(action, "_get_url"):
                if (
                    not action.get_url()
                    and not action.get_hx_get()
                    and not action.get_hx_post()
                    and not action.get_hx_delete()
                ):
                    # Legacy actions are mutable. Clone before filling in a
                    # default URL so a shared Resource declaration is not
                    # changed by one request.
                    from copy import copy

                    action = copy(action)
                    prefix = self.config.resource_prefix or ""
                    action.hx(get=f"{prefix.rstrip('/')}/create")

                from lexigram.admin.ui.organisms.data_table.actions import (
                    render_action_button,
                )

                node = render_action_button(
                    action,
                    resource_name=self.config.resource_name,
                    resource_prefix=self.config.resource_prefix,
                    form_display_mode=getattr(self.config, "form_display_mode", None),
                )
                if node:
                    header_buttons.append(node)
                continue

            from lexigram.admin.actions.types import ActionContext as _ActionContext

            ctx = _ActionContext(
                user=self.user,
                resource_name=self.config.resource_name or "",
                resource_prefix=self.config.resource_prefix or "",
                metadata={
                    "form_display_mode": getattr(
                        self.config, "form_display_mode", "slider"
                    )
                },
            )
            url = action._get_url(None, ctx)
            htmx_attrs = action._get_htmx_attrs(url, None, ctx) if url else {}

            btn = ActionButton(
                label=action.label,
                icon=action.icon,
                variant=action._color_to_variant(),
                **htmx_attrs,
            )
            header_buttons.append(btn.render())

        # 2. Bulk Actions (shown only when items selected)
        # Wrap all bulk actions in a single container with x-show/x-cloak for efficiency
        bulk_action_items = []
        if bulk_actions:
            # Selection counter — page-scoped, not cross-page
            bulk_action_items.append(
                el(
                    "span",
                    el("strong", x_text="selectedIds.length"),
                    " selected on this page",
                    class_="text-sm font-medium text-primary-600 dark:text-primary-400 mr-2",
                ),
            )

            for action in bulk_actions:
                if not action.is_visible(self.user):
                    continue

                # CSV is a browser download, not an HTMX fragment. XHR-based
                # ``hx-post`` responses do not honor Content-Disposition as a
                # download, so use the shared native-submit helper while still
                # carrying the checked row IDs and CSRF field.
                action_name = str(getattr(action, "name", ""))
                if action_name in {"export", "export_csv", "export_xlsx"}:
                    export_url = (
                        f"{(self.config.resource_prefix or '').rstrip('/')}/bulk"
                    )
                    _label = getattr(action, "label", None) or action_name
                    _icon_value = getattr(action, "icon", None)
                    _icon = (
                        _icon_value
                        if isinstance(_icon_value, str)
                        else getattr(action, "_icon", None)
                    )
                    if hasattr(action, "_color_to_variant"):
                        _color = action._color_to_variant()
                    else:
                        _raw_color = getattr(action, "_color", "secondary")
                        _color = (
                            "secondary"
                            if _raw_color == "primary"
                            else _raw_color
                            if _raw_color in ("secondary", "danger", "ghost")
                            else "secondary"
                        )
                    btn = ActionButton(
                        label=_label,
                        icon=_icon,
                        color=_color,
                        size="sm",
                        type="button",
                        data_bulk_download_url=export_url,
                        data_bulk_action=action_name,
                        onclick="return window.LexigramDownloadBulk(this);",
                    )
                    bulk_action_items.append(btn.render())
                    continue

                from lexigram.admin.actions.types import ActionContext as _ActionContext
                from lexigram.ui import HTMXAttrs

                _hx_delete = getattr(action, "_hx_delete", None)
                _hx_post = getattr(action, "_hx_post", None)

                if _hx_delete or _hx_post:
                    # Old-style action — use HTMXAttrs helper
                    _confirmation_message = getattr(
                        action, "_confirmation_message", None
                    )
                    _confirmation_title = getattr(action, "_confirmation_title", None)
                    _color = getattr(action, "_color", None)
                    _icon = getattr(action, "_icon", None)
                    _action_name = getattr(action, "name", "")

                    _method = "DELETE" if _hx_delete else "POST"
                    _url = _hx_delete or _hx_post or ""

                    bulk_attrs = HTMXAttrs.for_bulk_action(
                        url=_url,
                        method=_method,
                        confirm_message=_confirmation_message or _confirmation_title,
                        action_name=_action_name,
                    )

                    _variant = (
                        "secondary"
                        if _color == "primary"
                        else (
                            _color
                            if _color in ("secondary", "danger", "ghost")
                            else "secondary"
                        )
                    )
                    btn = ActionButton(
                        label=action.label,
                        color=_variant,
                        icon=_icon,
                        size="sm",
                        type="button",
                        **bulk_attrs,  # type: ignore[arg-type]
                    )
                else:
                    # New-style action — use _get_url + _get_htmx_attrs
                    ctx = _ActionContext(
                        user=self.user,
                        resource_name=self.config.resource_name or "",
                        resource_prefix=self.config.resource_prefix or "",
                    )
                    url = f"{ctx.resource_prefix.rstrip('/')}/bulk"
                    if hasattr(action, "_get_htmx_attrs"):
                        htmx_attrs = action._get_htmx_attrs(url, None, ctx)
                        from lexigram.serialization import dumps_str

                        htmx_attrs["hx-vals"] = dumps_str({"action": action.name})
                    else:
                        from lexigram.ui import HTMXAttrs

                        # Legacy declarations without an explicit HTMX
                        # endpoint still use the mounted generic bulk route;
                        # the action name is carried in the form payload.
                        _confirmation_message = getattr(
                            action, "_confirmation_message", None
                        ) or getattr(action, "_confirmation_title", None)
                        htmx_attrs = HTMXAttrs.for_bulk_action(
                            url=url,
                            method="POST",
                            action_name=action.name,
                            confirm_message=_confirmation_message
                            if getattr(action, "_requires_confirmation", False)
                            else None,
                        )
                    _label = getattr(action, "label", None) or action.name
                    _icon_value = getattr(action, "icon", None)
                    _icon = (
                        _icon_value
                        if isinstance(_icon_value, str)
                        else getattr(action, "_icon", None)
                    )
                    if hasattr(action, "_color_to_variant"):
                        _color = action._color_to_variant()
                    else:
                        _raw_color = getattr(action, "_color", "secondary")
                        _color = (
                            "secondary"
                            if _raw_color == "primary"
                            else _raw_color
                            if _raw_color in ("secondary", "danger", "ghost")
                            else "secondary"
                        )
                    btn = ActionButton(
                        label=_label,
                        icon=_icon,
                        color=_color,
                        size="sm",
                        type="button",
                        **htmx_attrs,
                    )
                bulk_action_items.append(btn.render())

        # Wrap bulk actions in a single hidden container (x-cloak + x-show on container)
        bulk_buttons = []
        if bulk_action_items:
            bulk_buttons.append(
                el(
                    "div",
                    *bulk_action_items,
                    class_="flex items-center gap-2",
                    x_cloak=True,
                    **{"x-show": "selectedIds.length > 0"},
                ),
            )

        # Structure: [Left: Switchers] [Right: Bulk Actions | Header Buttons]
        # - Bulk actions hidden until selected (x-show/x-cloak)
        # - Header buttons (Create) ALWAYS visible, ALWAYS on the right
        return el(
            "div",
            self._render_switchers(),
            # Right side: bulk actions (hidden) + header buttons (always visible)
            el(
                "div",
                # Bulk actions - only these have x-cloak/x-show
                *bulk_buttons,
                # Header buttons (Create) - NO x-cloak, always visible
                *header_buttons,
                class_="flex flex-wrap items-center gap-2",
            ),
            class_="flex flex-wrap gap-2 items-center justify-between mb-2 pb-2 border-b border-border",
            id=Zones.TOOLBAR.id,
        )

    def _render_switchers(self) -> Any:
        """Render the left-hand switcher cluster gated by ``data_view``."""
        caps = controls_for(getattr(self.state, "view", None))
        nodes: list[Any] = []

        if caps.layout:
            nodes.append(
                LayoutSwitcher(
                    current=self.state.layout,
                    resource_prefix=self.config.resource_prefix,
                    state=self.state,
                ).render()
            )

        # Highest-order structure: tabular / stacked / grid / calendar.
        nodes.append(
            ViewSwitcher(
                current=self.state.view,
                resource_prefix=self.config.resource_prefix,
                options=list(DATA_VIEW_OPTIONS),
                state=self.state,
            ).render()
        )

        if caps.toolbar_sort:
            nodes.append(
                SortSwitcher(
                    current=self.state.sort_by,
                    current_order=self.state.sort_order,
                    resource_prefix=self.config.resource_prefix,
                    columns=self.config.columns,
                    state=self.state,
                ).render()
            )

        if caps.group_by:
            nodes.append(
                GroupBySwitcher(
                    current=self.state.group_by or self.config.group_by,
                    resource_prefix=self.config.resource_prefix,
                    columns=self.config.columns,
                    state=self.state,
                ).render()
            )

        if caps.density:
            nodes.append(
                DensitySwitcher(
                    current=self.state.density or self.config.density,
                    resource_prefix=self.config.resource_prefix,
                    state=self.state,
                ).render()
            )

        if caps.column_visibility:
            nodes.append(
                ColumnVisibilitySwitcher(
                    columns=self.config.columns,
                    current_hidden=self.state.hidden_columns or [],
                    resource_prefix=self.config.resource_prefix,
                    state=self.state,
                ).render()
            )

        has_search_enabled = caps.search and self.config.enable_search
        has_filters_available = caps.filters and bool(self.config.filters)
        if self.config.resource_prefix and (
            has_search_enabled or has_filters_available
        ):
            from lexigram.ui import HTMXAttrs

            clear_state = self.state.clear_filters()
            clear_attrs = HTMXAttrs.for_full_refresh(
                state=clear_state,
                resource_prefix=self.config.resource_prefix,
                push_url=True,
            )
            nodes.append(
                ActionButton(
                    label="Clear",
                    variant="ghost",
                    icon="x",
                    size="sm",
                    **clear_attrs,  # type: ignore[arg-type]
                    **{  # type: ignore[arg-type]
                        "x-bind:class": (
                            "{ 'opacity-50 cursor-not-allowed': "
                            "!hasActiveFiltersState }"
                        ),
                        "x-bind:disabled": "!hasActiveFiltersState",
                        "@click": (
                            "if (!hasActiveFiltersState) $event.preventDefault()"
                        ),
                        "x-ref": "clearFiltersButton",
                    },
                ).render()
            )

        return el(
            "div",
            *nodes,
            class_="flex flex-wrap items-center gap-2",
            id=Zones.TOOLBAR.id + "-switchers",
        )

    def render_search(self) -> Any:
        if not controls_for(getattr(self.state, "view", None)).search:
            return ""
        if not self.config.enable_search:
            return ""

        search_query = self.state.search
        search_fields = self.config.search_fields or [
            c.name for c in self.config.columns if getattr(c, "_searchable", False)
        ]
        search_placeholder = (
            f"Search by {', '.join(search_fields)}..." if search_fields else "Search..."
        )

        # Use canonical live-table-input attrs (hx-include for state + search),
        # appending filters zone so filter values are preserved on search.
        from lexigram.ui import HTMXAttrs

        base_attrs = HTMXAttrs.for_live_table_input(
            self.state,
            self.config.resource_prefix or "",
        )
        search_attrs = {
            **base_attrs,
            "hx-trigger": "keyup changed delay:500ms, input, search",
            "hx-include": f"{base_attrs['hx-include']}, #{Zones.FILTERS.id}",
        }

        search_bar = SearchBar(
            name="search",
            value=search_query or "",
            placeholder=search_placeholder,
            show_icon=True,
            show_clear=True,
            **search_attrs,
        )
        return el("div", search_bar.render(), class_="flex-1 mb-2", id=Zones.SEARCH.id)

    def render_filters(self) -> Any:
        if not controls_for(getattr(self.state, "view", None)).filters:
            return ""
        active_filters = self.config.filters

        if not (self.config.resource_prefix and active_filters):
            return ""  # Return empty if no filters needed

        # Determine display mode based on layout
        fb_display = "vertical" if self.state.layout == "sidebar" else "horizontal"

        filter_bar = FilterBar(
            filters=active_filters or {},
            current_values=self.state.filters,
            resource_prefix=self.config.resource_prefix,
            display=fb_display,
            state=self.state,
            id=Zones.FILTERS.id,
        )
        return el("div", filter_bar.render(), class_="mb-4")

    def render_switchers_oob(self) -> Any:
        """
        Render just the switchers part of the toolbar with OOB swap.
        This allows updating the switcher links (state) without re-rendering
        the search bar (preserving focus).
        """
        switchers = self._render_switchers()
        switchers.attrs["hx_swap_oob"] = "outerHTML"
        return switchers
