from __future__ import annotations

from abc import ABC, abstractmethod
import re
from typing import Any

from lexigram.admin.ui.organisms.table.views.summarizers import compute_summaries
from lexigram.ui import Checkbox, el

HEADER_HEIGHT = 50

_ROW_HEIGHT_RE = re.compile(r"^\d+(px|rem|em|vh|%)$")


def _js_str(value: Any) -> str:
    """Escape a value for a single-quoted JavaScript string context.

    Composes with ``el()``'s HTML attribute escaping: the browser decodes
    HTML entities before Alpine.js compiles the attribute as JavaScript,
    so ``el()`` alone cannot neutralize a ``'`` breakout — this helper
    backslash-escapes every character that could terminate or alter the
    JS string.
    """
    s = str(value)
    return (
        s.replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace("\r", "\\r")
        .replace("\n", "\\n")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


class AbstractDataView(ABC):
    """Abstract Strategy for Data Visualization."""

    def __init__(
        self,
        data: list[dict],
        config: Any,
        state: Any,
        total: int = 0,
        summary: dict[str, Any] | None = None,
        user: Any = None,
        resource_name: str | None = None,
    ):
        self.data = data
        self.config = config
        self.state = state
        self.total = total
        self.summary = summary
        self.user = user
        self.resource_name = resource_name

        # Apply column ordering if present in state
        if self.state.column_order:
            ordered_cols = []
            col_map = {col.name: col for col in self.config.columns}
            for name in self.state.column_order:
                if name in col_map:
                    ordered_cols.append(col_map.pop(name))
            # Append any remaining columns not in the order list
            ordered_cols.extend(col_map.values())
            self.config.columns = ordered_cols

    @abstractmethod
    def render(self) -> Any:
        pass


class TabularView(AbstractDataView):
    """Render data as a standard HTML Table."""

    def render(self) -> Any:
        thead = self.render_header()
        tbody = el(
            "tbody",
            *self.render_rows(),
            class_="bg-card divide-y divide-border",
        )
        tfoot = (
            self.render_summary(self.effective_summary())
            if self.effective_summary()
            else ""
        )

        density_class = getattr(
            self.config, "density_css_class", "table-density-normal"
        )

        table_el = el(
            "table",
            thead,
            tbody,
            tfoot,
            class_="min-w-full divide-y divide-border border-separate border-spacing-0",
            style="table-layout: auto; min-width: 100%; width: max-content;",
        )

        return el(
            "div",
            table_el,
            class_=f"overflow-x-auto overflow-y-auto shadow-sm ring-1 ring-border dark:ring-border rounded-lg bg-muted/50 {density_class}",
            style="max-height: min(70vh, calc(100vh - var(--admin-table-offset, 18rem))); min-height: 200px;",
        )

    def render_header(self) -> Any:
        current_sort = self.state.sort_by
        current_order = self.state.sort_order

        # 1. Header Logic
        header_cells = []
        left_offset = 0

        # Checkbox header
        if self.config.resource_prefix and self.config.bulk_actions:
            all_ids = []
            for item in self.data:
                item_id = ""
                if isinstance(item, dict):
                    item_id = item.get("id", item.get("user_id", item.get("pk", "")))
                elif hasattr(item, "id"):
                    item_id = item.id
                elif hasattr(item, "user_id"):
                    item_id = item.user_id
                elif hasattr(item, "pk"):
                    item_id = item.pk
                elif hasattr(item, "__getitem__"):
                    try:
                        item_id = item[0]
                    except (IndexError, TypeError):
                        item_id = ""

                all_ids.append(str(item_id) if item_id is not None else "")

            # If any column is pinned left, bulk checkbox should also be pinned
            is_pinned = any(
                getattr(col, "_pinned", None) == "left" for col in self.config.columns
            )
            style = ""
            cls = (
                "px-6 py-3 text-left w-12 sticky top-0 z-30 bg-muted dark:bg-background"
            )
            if is_pinned:
                style = f"left: {left_offset}px"
                cls += " border-r border-border"
                left_offset += 48  # Approximate w-12 width

            select_all_attrs: dict[str, Any] = {
                "aria-label": "Select all rows on this page",
                ":checked": "allIds.length > 0 && selectedIds.length === allIds.length",
                "x-effect": "$el.indeterminate = selectedIds.length > 0 && selectedIds.length < allIds.length",
                "@change": "handleSelectAll($event)",
            }
            header_cells.append(
                el(
                    "th",
                    Checkbox(name="select_all", **select_all_attrs),
                    class_=cls,
                    style=style,
                ),
            )
        elif self.config.resource_prefix:
            pass

        # Spacer for expandable
        if self.config.expandable_relationship:
            header_cells.append(
                el(
                    "th",
                    "",
                    class_="px-6 py-3 text-left w-12 sticky top-0 z-20 bg-muted dark:bg-background",
                ),
            )

        for col in self.config.columns:
            if not col.is_visible(user=self.user, resource_name=self.resource_name):
                continue
            header_th = col.render_header(
                current_sort,
                current_order,
                state=self.state,
                resource_prefix=getattr(self.config, "resource_prefix", ""),
            )

            # Ensure standard headers are also sticky
            if hasattr(header_th, "attrs"):
                header_th.attrs["class_"] = (
                    header_th.attrs.get("class_", "")
                    + " sticky top-0 z-20 bg-muted dark:bg-background group"
                )
                header_th.attrs["data-col-name"] = col.name

                # Style handling: apply explicit width styles when provided
                # Otherwise, if grow() is enabled, mark the inner wrapper as fluid (w-full + min-w-0)
                col_width = getattr(col, "_width", None)
                col_grow = getattr(col, "_grow", True)

                if col_width is not None:
                    # Numeric widths => treat as rem units; string widths passthrough
                    if isinstance(col_width, (int, float)):
                        style_val = f"{float(col_width)}rem"
                    else:
                        style_val = str(col_width)
                    existing_style = header_th.attrs.get("style", "")
                    header_th.attrs["style"] = (
                        existing_style + f"; width: {style_val}; min-width: {style_val}"
                    ).strip("; ")
                elif col_grow:
                    # Try to add grow classes to the inner wrapper if present
                    if getattr(header_th, "children", None):
                        inner = header_th.children[0]
                        if hasattr(inner, "attrs"):
                            inner.attrs["class"] = (
                                inner.attrs.get("class", "") + " w-full min-w-0"
                            ).strip()

                # Add Reordering support
                if getattr(self.config, "reorderable_columns", False):
                    # Add drag handle before the header content
                    drag_handle = el(
                        "span",
                        el(
                            "i",
                            class_="fas fa-grip-vertical text-muted-foreground opacity-0 group-hover:opacity-100 cursor-move mr-1",
                        ),
                        class_="drag-handle inline-flex items-center",
                        **{
                            "draggable": "true",
                            "@dragstart": f"event.dataTransfer.setData('text/plain', '{col.name}')",
                            "@dragover.prevent": "",
                            "@drop": f"reorderColumn(event.dataTransfer.getData('text/plain'), '{col.name}')",
                        },
                    )
                    header_th.children.insert(0, drag_handle)

            if getattr(col, "_pinned", None) == "left":
                if hasattr(header_th, "attrs"):
                    header_th.attrs["class_"] = (
                        header_th.attrs.get("class_", "")
                        + " sticky left-0 z-30 border-r border-border"
                    )
                    header_th.attrs["style"] = (
                        header_th.attrs.get("style", "") + f"; left: {left_offset}px"
                    ).strip("; ")

                col_width = getattr(col, "_width", None) or 150
                left_offset += col_width

            header_cells.append(header_th)

        if self.config.resource_prefix:
            header_cells.append(
                el(
                    "th",
                    "Actions",
                    scope="col",
                    class_="px-6 py-3 text-right text-xs uppercase tracking-wider text-muted-foreground font-medium sticky top-0 z-20 bg-muted dark:bg-background",
                ),
            )

        # Ensure header row has fixed height to match body rows and remains sticky
        return el(
            "thead",
            el(
                "tr",
                *header_cells,
                class_="bg-muted dark:bg-card/50 border-b border-border",
                style="height: 60px;",
            ),
        )

    def render_rows(self) -> list[Any]:
        body_rows = []

        # Determine grouping
        group_col = self.config.group_by

        # Sort data for grouping if needed (groupby requires sorted data)
        # We assume data might be paginated, so this grouping applies to the current page.
        data_to_render = self.data
        if group_col:
            from itertools import groupby

            # Sort stable to keep existing order within groups if possible,
            # though usually data comes sorted from DB.
            # We strictly sort by group key to ensure groupby works correctly.
            def get_group_key(x) -> Any:
                val = (
                    x.get(group_col)
                    if isinstance(x, dict)
                    else getattr(x, group_col, None)
                )
                return str(val if val is not None else "Unknown")

            data_to_render = sorted(self.data, key=get_group_key)

            # Create groups
            grouped_data = groupby(data_to_render, key=get_group_key)

            for group_name, items in grouped_data:
                group_items = list(items)

                # Render Group Header
                colspan = (
                    len(self.config.columns)
                    + (
                        1
                        if self.config.resource_prefix and self.config.bulk_actions
                        else 0
                    )
                    + (1 if self.config.expandable_relationship else 0)
                    + (1 if self.config.resource_prefix else 0)
                )  # Actions column

                group_header = el(
                    "tr",
                    el(
                        "td",
                        el(
                            "button",
                            el(
                                "i",
                                class_="fas fa-chevron-down mr-2 transition-transform duration-200",
                                **{
                                    ":class": f"{{ '-rotate-90': collapsedGroups.includes('{_js_str(group_name)}') }}",
                                },
                            ),
                            el(
                                "span",
                                group_name,
                                class_="font-semibold text-foreground",
                            ),
                            el(
                                "span",
                                f"({len(group_items)})",
                                class_="ml-2 text-sm text-muted-foreground font-normal",
                            ),
                            type="button",
                            class_="flex items-center w-full text-left focus:outline-none",
                            **{"@click": f"toggleGroup('{_js_str(group_name)}')"},
                        ),
                        colspan=colspan,
                        class_="px-6 py-3 bg-muted/80 dark:bg-card/80 border-b border-border backdrop-blur-sm sticky left-0 z-10",
                    ),
                    class_="group-header",
                )
                body_rows.append(group_header)

                # Render Items in Group
                for i, item in enumerate(group_items):
                    self._render_single_row(item, i, body_rows, group_name)

        else:
            # Standard non-grouped rendering
            for i, item in enumerate(self.data):
                self._render_single_row(item, i, body_rows, None)

        return body_rows

    def _render_single_row(
        self,
        item: dict | Any,
        index: int,
        output_list: list,
        group_key: str | None,
    ) -> Any:
        cells = []
        row_left_offset = 0
        rid = ""
        if isinstance(item, dict):
            rid = str(item.get("id", item.get("user_id", item.get("pk", ""))))
        elif hasattr(item, "id"):
            rid = str(item.id)
        elif hasattr(item, "user_id"):
            rid = str(item.user_id)
        elif hasattr(item, "pk"):
            rid = str(item.pk)
        elif hasattr(item, "__getitem__"):
            try:
                rid = str(item[0])
            except (IndexError, TypeError):
                rid = ""

        # Checkbox cell
        if self.config.resource_prefix and self.config.bulk_actions:
            is_pinned = any(
                getattr(col, "_pinned", None) == "left" for col in self.config.columns
            )
            cls = "px-6 py-4 whitespace-nowrap w-12 z-20 bg-inherit"
            style = ""
            if is_pinned:
                cls += " sticky left-0 border-r border-border"
                style = f"left: {row_left_offset}px"
                row_left_offset += 48

            td_attrs: dict[str, Any] = {
                "@click": f"handleSelect('{_js_str(rid)}', $event)",
            }
            cell_attrs: dict[str, Any] = {"@click.stop": ""}
            cells.append(
                el(
                    "td",
                    Checkbox(
                        name="ids",
                        value=rid,
                        x_model="selectedIds",
                        aria_label=f"Select row {rid}",
                        **cell_attrs,
                    ),
                    class_=cls,
                    style=style,
                    **td_attrs,
                ),
            )

        # Expandable Toggle
        if self.config.expandable_relationship:
            toggle_btn = el(
                "button",
                el(
                    "svg",
                    el(
                        "path",
                        **{
                            "d": "M9 5l7 7-7 7",
                            "stroke-linecap": "round",
                            "stroke-linejoin": "round",
                            "stroke-width": "2",
                        },
                    ),
                    class_="w-4 h-4 transition-transform duration-200",
                    viewBox="0 0 24 24",
                    stroke="currentColor",
                    fill="none",
                    aria_hidden="true",
                    **{
                        ":class": f"{{ 'rotate-90': expandedIds.includes('{_js_str(rid)}') }}"
                    },
                ),
                type="button",
                aria_label=f"Toggle details for row {rid}",
                class_="p-1 rounded hover:bg-muted text-muted-foreground",
                **{
                    ":aria-expanded": f"expandedIds.includes('{_js_str(rid)}')",
                    "@click": f"toggleExpand('{_js_str(rid)}')",
                },
            )
            cells.append(
                el("td", toggle_btn, class_="px-6 py-4 whitespace-nowrap w-12"),
            )

        # Data cells
        for col in self.config.columns:
            if not col.is_visible(
                user=self.user,
                resource_name=self.resource_name,
                record=item,
            ):
                continue
            cell_td = col.render_cell(
                item,
                user=self.user,
                resource_name=self.resource_name,
            )

            # Style behavior for cells: if column has an explicit width, apply it
            # (numeric -> rem units; string -> passthrough). Otherwise, if grow is enabled
            # mark the cell as fluid with Tailwind classes so the browser distributes space.
            col_width = getattr(col, "_width", None)
            col_grow = getattr(col, "_grow", True)

            if col_width is not None:
                if isinstance(col_width, (int, float)):
                    style_val = f"{float(col_width)}rem"
                else:
                    style_val = str(col_width)
                if hasattr(cell_td, "attrs"):
                    existing_style = cell_td.attrs.get("style", "")
                    cell_td.attrs["style"] = (
                        existing_style + f"; width: {style_val}; min-width: {style_val}"
                    ).strip("; ")
            elif col_grow:
                if hasattr(cell_td, "attrs"):
                    cell_td.attrs["class_"] = (
                        cell_td.attrs.get("class_", "") + " w-full min-w-0"
                    ).strip()

            if getattr(col, "_pinned", None) == "left":
                if hasattr(cell_td, "attrs"):
                    cell_td.attrs["class_"] = (
                        cell_td.attrs.get("class_", "")
                        + " sticky left-0 z-20 border-r border-border bg-inherit"
                    )
                    cell_td.attrs["style"] = (
                        cell_td.attrs.get("style", "") + f"; left: {row_left_offset}px"
                    ).strip("; ")

                col_width_pinned = getattr(col, "_width", None) or 150
                row_left_offset += col_width_pinned

            cells.append(cell_td)

        # Actions cell
        if self.config.resource_prefix:
            from lexigram.admin.ui.organisms.data_table.actions import (
                render_action_button,
            )

            action_nodes = []
            for action in self.config.actions:
                node = render_action_button(
                    action,
                    record=item,
                    user=self.user,
                    resource_name=self.resource_name,
                    resource_prefix=self.config.resource_prefix,
                )
                if node:
                    action_nodes.append(node)

            # Allow configurable action layout: 'horizontal' (default) or 'stack'
            layout = getattr(self.config, "_action_layout", None) or getattr(
                self.config,
                "action_layout",
                "horizontal",
            )
            if layout in ("stack", "vertical"):
                action_container_cls = "flex flex-col items-end gap-2 relative z-10"
            else:
                action_container_cls = (
                    "flex items-center gap-2 justify-end relative z-10"
                )

            cells.append(
                el(
                    "td",
                    el("div", *action_nodes, class_=action_container_cls),
                    class_="px-6 py-4 whitespace-nowrap text-right text-sm",
                ),
            )

        row_height = str(getattr(self.config, "density_row_height", "48px"))
        if not _ROW_HEIGHT_RE.fullmatch(row_height):
            row_height = "48px"
        row_attrs = {
            "class_": "hover:bg-muted dark:hover:bg-card/80 transition-shadow duration-150 border-b border-border last:border-0 group",
            ":class": f"{{ 'bg-primary-50/50 dark:bg-primary-900/30 ring-inset ring-2 ring-primary-500/50 z-10 relative': $data.focusedId === '{_js_str(rid)}', 'bg-muted/30': {index} % 2 === 1 }}",
            "style": f"height: {row_height};",
        }

        if group_key:
            row_attrs["x-show"] = f"!collapsedGroups.includes('{_js_str(group_key)}')"
            row_attrs["x-transition"] = ""

        output_list.append(el("tr", *cells, **{**row_attrs, "data-row-id": rid}))

        # Expandable Row (Detail)
        if self.config.expandable_relationship:
            colspan = (
                len(self.config.columns)
                + (1 if self.config.resource_prefix else 0)
                + 1
                + (1 if self.config.bulk_actions else 0)
            )
            detail_url = f"{self.config.resource_prefix}/{rid}/relations/{self.config.expandable_relationship}"

            detail_attrs = {
                "x-show": f"expandedIds.includes('{_js_str(rid)}')",
                "x-transition": "",
            }
            # Also collapse detail if group is collapsed
            if group_key:
                detail_attrs["x-show"] = (
                    f"expandedIds.includes('{_js_str(rid)}') && "
                    f"!collapsedGroups.includes('{_js_str(group_key)}')"
                )

            detail_row = el(
                "tr",
                el(
                    "td",
                    el(
                        "div",
                        el(
                            "div",
                            "Loading relationship...",
                            class_="animate-pulse text-muted-foreground text-sm p-4",
                        ),
                        **{"hx-get": detail_url, "hx-trigger": "intersect once"},
                    ),
                    colspan=colspan,
                    class_="px-0 py-0 border-b border-border bg-muted/50 dark:bg-background/50",
                ),
                **detail_attrs,
            )
            output_list.append(detail_row)

    def effective_summary(self) -> dict[str, Any] | None:
        """Resolve footer summaries: explicit summary or per-column aggregates."""
        if self.summary:
            return self.summary
        computed = compute_summaries(self.data, self.config.columns)
        return computed or None

    def render_summary(self, summary: dict[str, Any] | None = None) -> Any:
        summary_cells = []
        left_offset = 0

        # Checkbox column
        if self.config.resource_prefix and self.config.bulk_actions:
            is_pinned = any(
                getattr(col, "_pinned", None) == "left" for col in self.config.columns
            )
            cls = "px-6 py-3 sticky bottom-0 z-30 bg-muted dark:bg-background border-t border-border"
            style = ""
            if is_pinned:
                style = f"left: {left_offset}px"
                cls += " border-r"
                left_offset += 48
            summary_cells.append(el("td", "", class_=cls, style=style))

        # Expandable spacer
        if self.config.expandable_relationship:
            summary_cells.append(
                el(
                    "td",
                    "",
                    class_="px-6 py-3 sticky bottom-0 z-20 bg-muted dark:bg-background border-t border-border",
                ),
            )

        # Data columns
        for col in self.config.columns:
            val = summary.get(col.name, "") if summary else ""
            cls = "px-6 py-3 text-sm font-bold text-foreground sticky bottom-0 z-20 bg-muted dark:bg-background border-t border-border"
            style = ""

            if getattr(col, "_pinned", None) == "left":
                cls += " sticky left-0 z-30 border-r"
                style = f"left: {left_offset}px"
                left_offset += getattr(col, "_width", None) or 150

            summary_cells.append(el("td", str(val), class_=cls, style=style))

        # Actions column
        if self.config.resource_prefix:
            summary_cells.append(
                el(
                    "td",
                    "",
                    class_="px-6 py-3 sticky bottom-0 z-20 bg-muted dark:bg-background border-t border-border",
                ),
            )

        return el("tfoot", el("tr", *summary_cells, style="height: 50px;"))
