"""Row and cell rendering for TabularView."""

from __future__ import annotations

import re
from typing import Any

from lexigram.ui import Checkbox, el

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


def get_attr(item: Any, key: str, default: Any = None) -> Any:
    """Safely read an attribute from dict-like or attribute-like records."""
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def extract_row_id(item: Any) -> str:
    """Resolve a stable, non-empty string id from a record.

    ``None`` is not an identifier: converting it to the literal string
    ``"None"`` would make an id-less row look selectable and could send a
    synthetic value to a destructive endpoint.
    """
    value: Any = None
    found = False
    if isinstance(item, dict):
        for key in ("id", "user_id", "pk"):
            if key in item:
                value = item[key]
                found = True
                break
    else:
        for key in ("id", "user_id", "pk"):
            if hasattr(item, key):
                value = getattr(item, key)
                found = True
                break
        if not found and hasattr(item, "__getitem__"):
            try:
                value = item[0]
                found = True
            except (IndexError, KeyError, TypeError):
                pass
    if not found or value is None:
        return ""
    return str(value).strip()


def render_table_rows(
    config: Any,
    data: list[Any],
    user: Any,
    resource_name: str | None,
) -> list[Any]:
    """Render all body rows (grouped when ``config.group_by`` is set)."""
    body_rows = []

    # Determine grouping
    group_col = config.group_by

    # Sort data for grouping if needed (groupby requires sorted data)
    # We assume data might be paginated, so this grouping applies to the current page.
    data_to_render = data
    if group_col:
        from itertools import groupby

        # Sort stable to keep existing order within groups if possible,
        # though usually data comes sorted from DB.
        # We strictly sort by group key to ensure groupby works correctly.
        def get_group_key(x: Any) -> Any:
            val = (
                x.get(group_col) if isinstance(x, dict) else getattr(x, group_col, None)
            )
            return str(val if val is not None else "Unknown")

        data_to_render = sorted(data, key=get_group_key)

        # Create groups
        grouped_data = groupby(data_to_render, key=get_group_key)

        for group_name, items in grouped_data:
            group_items = list(items)

            # Render Group Header
            colspan = (
                len(config.columns)
                + (1 if config.resource_prefix and config.bulk_actions else 0)
                + (1 if config.expandable_relationship else 0)
                + (1 if config.resource_prefix else 0)
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
                body_rows.extend(
                    _render_single_row(config, user, resource_name, item, i, group_name)
                )

    else:
        # Standard non-grouped rendering
        for i, item in enumerate(data):
            body_rows.extend(
                _render_single_row(config, user, resource_name, item, i, None)
            )

    return body_rows


def _render_single_row(
    config: Any,
    user: Any,
    resource_name: str | None,
    item: dict | Any,
    index: int,
    group_key: str | None,
) -> list[Any]:
    cells = []
    row_left_offset = 0
    rid = extract_row_id(item)
    has_row_id = bool(rid)

    # Checkbox cell
    if config.resource_prefix and config.bulk_actions and rid:
        is_pinned = any(
            getattr(col, "_pinned", None) == "left" for col in config.columns
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
    if config.expandable_relationship and has_row_id:
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
    for col in config.columns:
        if not col.is_visible(
            user=user,
            resource_name=resource_name,
            record=item,
        ):
            continue
        cell_td = col.render_cell(
            item,
            user=user,
            resource_name=resource_name,
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
    if config.resource_prefix:
        from lexigram.admin.ui.organisms.data_table.actions import (
            render_action_button,
        )

        action_nodes = []
        for action in config.actions if has_row_id else ():
            node = render_action_button(
                action,
                record=item,
                user=user,
                resource_name=resource_name,
                resource_prefix=config.resource_prefix,
                form_display_mode=getattr(config, "form_display_mode", None),
            )
            if node:
                action_nodes.append(node)

        # Allow configurable action layout: 'horizontal' (default) or 'stack'
        layout = getattr(config, "_action_layout", None) or getattr(
            config, "action_layout", "horizontal"
        )
        if layout in ("stack", "vertical"):
            action_container_cls = "flex flex-col items-end gap-2 relative z-10"
        else:
            action_container_cls = "flex items-center gap-2 justify-end relative z-10"

        cells.append(
            el(
                "td",
                el("div", *action_nodes, class_=action_container_cls),
                class_="px-6 py-4 whitespace-nowrap text-right text-sm",
            ),
        )

    row_height = str(getattr(config, "density_row_height", "48px"))
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

    rendered: list[Any] = [el("tr", *cells, **{**row_attrs, "data-row-id": rid})]

    # Expandable Row (Detail)
    if config.expandable_relationship and has_row_id:
        colspan = (
            len(config.columns)
            + (1 if config.resource_prefix else 0)
            + 1
            + (1 if config.bulk_actions else 0)
        )
        detail_url = (
            f"{config.resource_prefix}/{rid}/relations/{config.expandable_relationship}"
        )

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
        rendered.append(detail_row)

    return rendered
