"""Main rendering logic for data table component with HTMX/Alpine integration."""

from __future__ import annotations

import copy
from typing import Any
from urllib.parse import urlencode

from lexigram.admin.config import TableConfiguration
from lexigram.admin.resources.config import clone_table_configuration
from lexigram.admin.ui.organisms.data_table.actions import ActionManager
from lexigram.admin.ui.organisms.data_table.layout import LayoutComposer
from lexigram.admin.ui.organisms.data_table.states import StateRenderer
from lexigram.admin.ui.organisms.data_table.views import view_strategy_registry
from lexigram.admin.ui.organisms.pagination import Pagination
from lexigram.serialization import dumps_str
from lexigram.ui import TableState, Zones, el, raw, render_to_string


class DataTableRenderer:
    """Main renderer for data table component."""

    def __init__(
        self,
        data: list[dict],
        config: TableConfiguration,
        state: TableState,
        total: int | None = None,
        user: Any = None,
        loading: bool = False,
        error: Any = None,
        next_cursor: str | None = None,
        summary: dict[str, Any] | None = None,
        props: dict[str, Any] | None = None,
    ):
        self.data = data
        # Keep rendering side effects local. In particular, ActionManager adds
        # defaults and view strategies may reorder columns.
        self.config = clone_table_configuration(config)
        # Per-request density: the state's density (URL-driven) wins over the
        # resource-level default so each user's choice applies without
        # mutating the shared resource configuration.
        if state.density:
            self.config.density = state.density
        self.state = state
        self.total = total
        self.user = user
        self.loading = loading
        self.error = error
        self.next_cursor = next_cursor
        self.summary = summary
        self.props = props or {}

        # Permission state: framework never binds a permission service at
        # construction time; async callers hoist checks and inject the dict.
        supplied_permissions = (props or {}).get("permissions")
        if supplied_permissions is None:
            self.permissions = {
                "can_view": True,
                "can_create": True,
                "can_update": True,
                "can_delete": True,
            }
        else:
            self.permissions = {
                permission: bool(supplied_permissions.get(permission, False))
                for permission in (
                    "can_view",
                    "can_create",
                    "can_update",
                    "can_delete",
                )
            }

        self.action_manager = ActionManager(self.config, self.permissions)
        self.action_manager.configure_actions()

        self.layout_composer = LayoutComposer(self.config, state)
        self.state_renderer = StateRenderer(self.config, state)

        # Pre-compute IDs
        self._all_ids = self._extract_all_ids()

    def _extract_all_ids(self) -> list[str]:
        """Extract all record IDs from data."""
        from lexigram.admin.ui.organisms.table.views.tabular_rows import (
            extract_row_id,
        )

        # Bulk operations require an addressable record. Do not put empty IDs
        # into Alpine's selection set, otherwise several id-less rows collapse
        # into one selected value and a destructive action can target the wrong
        # server record.
        return [
            row_id
            for item in self.data
            if (row_id := extract_row_id(item))
        ]

    @property
    def all_ids_json(self) -> str:
        """JSON serialization of all IDs for Alpine.js."""
        return dumps_str(self._all_ids)

    def render(self) -> str:
        """Render the complete data table."""
        can_view = self.permissions.get("can_view", True)

        # Toolbar sections are not useful when the view itself is denied and
        # can accidentally reveal action affordances. Keep the denied state
        # deliberately data-free.
        toolbar = self._render_toolbar() if can_view else {}
        header_section = toolbar.get("header", "")
        search_section = toolbar.get("search", "")
        filter_section = toolbar.get("filter", "")

        is_htmx = self.props.get("htmx_request", False)

        # Scope tabs — inline for full render, OOB for HTMX data-only
        tabs_html = ""
        if can_view and not (self.props.get("render_fragment") or is_htmx):
            tabs_html = self._render_scope_tabs()

        # View content
        view_content = self._render_view_content()

        # Pagination
        pagination_el = self._render_pagination()

        # Hidden state inputs
        hidden_state_inputs = self._render_hidden_inputs()

        # Table content
        table_content = el(
            "div",
            *hidden_state_inputs,
            view_content,
            pagination_el if pagination_el else "",
            id=Zones.DATA.id,
        )

        # HTMX wrapper
        table_wrapper = self._render_htmx_wrapper(table_content)

        # Fragment logic
        if self.props.get("render_fragment", False):
            return render_to_string(table_wrapper)

        # HTMX data-only request: return data zone + OOB control fragments
        if is_htmx:
            oob_fragments = self._render_oob_fragments()
            return render_to_string([table_wrapper, *oob_fragments])

        if self.props.get("render_controls", False):
            return render_to_string(header_section)

        # Form wrapper
        inner_form = el(
            "form",
            table_wrapper,
            method="get",
            x_ref="bulkForm",
            class_="space-y-4",
            **{"@submit.prevent": ""},
        )

        # Layout composition
        container = self.layout_composer.compose(
            search_section,
            filter_section,
            inner_form,
        )

        # Script and final markup
        script = self._render_script()

        return render_to_string(
            [
                script,
                el(
                    "div",
                    raw(header_section),
                    raw(tabs_html),
                    container,
                    id=Zones.TABLE.id,
                    x_data=f"{{ selectedIds: [], expandedIds: [], collapsedGroups: [], lastSelected: null, focusedId: null, hasActiveFiltersState: false, allIds: {self.all_ids_json}, ...window.LexigramTableLogic }}",
                    **{
                        "@keydown.window": "handleKeydown($event)",
                        "@htmx:after-swap.window": "$nextTick(() => updateActiveFiltersState())",
                        "@input.window": f"if ($event.target.closest('{Zones.SEARCH.selector}') || $event.target.closest('{Zones.FILTERS.selector}')) $nextTick(() => updateActiveFiltersState())",
                        "@change.window": f"if ($event.target.closest('{Zones.SEARCH.selector}') || $event.target.closest('{Zones.FILTERS.selector}')) $nextTick(() => updateActiveFiltersState())",
                    },
                ),
            ],
        )

    def _render_toolbar(self) -> dict[str, Any]:
        """Render toolbar sections."""
        from lexigram.admin.ui.organisms.table.toolbar import TableToolbar

        toolbar = TableToolbar(self.config, self.state, user=self.user)
        return {
            "header": toolbar.render_header(bulk_actions=self.config.bulk_actions)
            if self.config.resource_prefix
            else "",
            "search": toolbar.render_search() if self.config.resource_prefix else "",
            "filter": toolbar.render_filters(),
        }

    def _render_scope_tabs(self, oob: bool = False) -> str:
        """Render Active/Trash scope tabs for soft-delete toggling."""
        from lexigram.ui import HTMXAttrs

        state = self.state
        prefix = self.config.resource_prefix or ""
        active = not state.include_deleted

        active_state = state.with_include_deleted(False)
        trash_state = state.with_include_deleted(True)

        active_url = active_state.to_url(prefix)
        trash_url = trash_state.to_url(prefix)

        active_attrs = HTMXAttrs.for_full_refresh(active_state, prefix, push_url=True)
        trash_attrs = HTMXAttrs.for_full_refresh(trash_state, prefix, push_url=True)

        def _tab(label: str, is_active: bool, url: str, htmx_attrs: dict) -> Any:
            """Render a single tab button or link."""
            cls = (
                "px-4 py-2 text-sm font-medium border-b-2 transition-colors "
                "border-primary-500 text-primary-600"
                if is_active
                else (
                    "px-4 py-2 text-sm font-medium border-b-2 transition-colors "
                    "border-transparent text-muted-foreground hover:text-foreground "
                    "hover:border-border"
                )
            )

            if is_active:
                return el("span", label, class_=cls)

            return el(
                "a",
                label,
                href=url,
                class_=cls,
                **htmx_attrs,
            )

        outer_attrs: dict[str, Any] = {"class_": "mb-4", "id": "table-scope-tabs"}
        if oob:
            outer_attrs["hx_swap_oob"] = "outerHTML"

        return render_to_string(
            el(
                "div",
                el(
                    "div",
                    el(
                        "nav",
                        _tab("Active", active, active_url, active_attrs),
                        _tab("Trash", not active, trash_url, trash_attrs),
                        class_="flex space-x-8 border-b border-border",
                    ),
                    class_="px-6",
                ),
                **outer_attrs,
            )
        )

    def _render_oob_fragments(self) -> list[Any]:
        """Render OOB fragments for toolbar controls during data-only HTMX requests.

        Returns a list of htpy elements with hx-swap-oob attributes.
        """
        if not self.permissions.get("can_view", True):
            return []

        from lexigram.admin.ui.organisms.table.toolbar import TableToolbar

        fragments: list[Any] = []

        # Toolbar switchers + clear button (existing OOB method)
        toolbar = TableToolbar(self.config, self.state, user=self.user)
        switchers = toolbar.render_switchers_oob()
        if switchers is not None:
            fragments.append(switchers)

        # Scope tabs as OOB fragment
        tabs = self._render_scope_tabs(oob=True)
        if tabs:
            fragments.append(tabs)

        return fragments

    def _render_view_content(self) -> Any:
        """Render the appropriate view content based on state."""
        if not self.permissions.get("can_view", True):
            return self.state_renderer.render_permission_denied()
        if self.loading:
            return self.state_renderer.render_skeleton()
        if self.error:
            return self.state_renderer.render_error(self.error)
        if not self.data:
            return self.state_renderer.render_empty()
        view_strategy = view_strategy_registry.create_view(
            self.state.view or "tabular",
            self.data,
            self._view_config(),
            self.state,
            self.total,
            self.summary,
            self.user,
            self.config.resource_name,
            next_cursor=self.next_cursor,
        )
        return view_strategy.render()

    def _view_config(self) -> Any:
        """Return the configuration with URL-hidden columns removed.

        Column visibility is a per-request concern (``TableState.hidden_columns``)
        and must not mutate the shared resource configuration. The toolbar and
        the column-visibility switcher keep the full column list via
        ``self.config``; only the rendered view drops hidden columns, so
        colspan/pinned-offset math stays consistent within the view.
        """
        hidden = set(self.state.hidden_columns or [])
        if not hidden:
            return self.config
        view_config = copy.copy(self.config)
        view_config.columns = [
            column
            for column in self.config.columns
            if getattr(column, "name", column) not in hidden
        ]
        return view_config

    def _render_pagination(self) -> Any:
        """Render pagination if needed."""
        if not self.permissions.get("can_view", True):
            return None
        if self.total is None or self.total <= 0:
            return None

        params = self.state.to_query_params()
        params.pop("page", None)
        params.pop("per_page", None)
        base_query = "&" + urlencode(params, doseq=True) if params else ""
        base_url = (
            f"{self.config.resource_prefix}/" if self.config.resource_prefix else ""
        )

        return Pagination(
            page=self.state.page,
            total=self.total,
            per_page=self.state.per_page,
            base_url=base_url,
            extra_query=base_query,
            hx_target=Zones.DATA.selector,
            hx_swap="innerHTML",
            show_size_selector=True,
            next_cursor=self.next_cursor,
            state=self.state,
        )

    def _render_hidden_inputs(self) -> list[Any]:
        """Render hidden inputs for state preservation."""
        exclude_keys = ["page", "per_page"]
        if self.config.enable_search:
            exclude_keys.append("search")

        if self.config.filters:
            if isinstance(self.config.filters, list):
                for filter_config in self.config.filters:
                    name = getattr(filter_config, "name", None)
                    if name:
                        exclude_keys.extend((name, f"filter_{name}"))
            elif isinstance(self.config.filters, dict):
                for name in self.config.filters:
                    exclude_keys.extend((name, f"filter_{name}"))

        return self.state.render_hidden_inputs(exclude=exclude_keys)

    def _render_htmx_wrapper(self, table_content: Any) -> Any:
        """Render HTMX wrapper with appropriate attributes."""
        from lexigram.ui import HTMXAttrs

        htmx_attrs = {}
        if self.state and self.config.resource_prefix:
            htmx_attrs = HTMXAttrs.for_data_refresh(
                self.state,
                self.config.resource_prefix,
                push_url=False,
            )

        return el(
            "div",
            table_content,
            id=Zones.TABLE.id + "-inner",
            hx_trigger="refreshTable from:body",
            hx_disinherit="hx-select",
            **htmx_attrs,
        )

    def _render_script(self) -> str:
        """Render Alpine.js script."""
        from lexigram.ui import DataTableScriptRenderer

        return DataTableScriptRenderer.render(self._all_ids)

    def render_bulk_actions(self) -> Any:
        """Render bulk actions bar."""
        if not self.config.bulk_actions:
            return None

        from lexigram.admin.ui.organisms.data_table.actions import (
            render_bulk_action_button,
        )

        bulk_buttons = []
        for action in self.config.bulk_actions:
            if not action.is_visible(None):
                continue
            btn = render_bulk_action_button(
                action,
                resource_name=self.config.resource_name,
                resource_prefix=self.config.resource_prefix,
            )
            if btn:
                bulk_buttons.append(btn)

        return el(
            "div",
            el(
                "div",
                el(
                    "span",
                    el("strong", x_text="selectedIds.length"),
                    " items selected",
                    class_="text-sm font-medium text-primary-600 dark:text-primary-400 mr-2",
                ),
                *bulk_buttons,
                class_="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 py-3 flex items-center justify-between",
            ),
            role="alert",
            aria_live="polite",
            class_="fixed bottom-0 left-0 right-0 bg-card dark:bg-background border-t border-border shadow-lg transition-transform duration-200 z-50",
            x_show="selectedIds.length > 0",
            style="display: none;",
            **{
                "x-transition:enter": "transform ease-out duration-200",
                "x-transition:enter-start": "translate-y-full",
                "x-transition:enter-end": "translate-y-0",
                "x-transition:leave": "transform ease-in duration-200",
                "x-transition:leave-start": "translate-y-0",
                "x-transition:leave-end": "translate-y-full",
            },
        )
