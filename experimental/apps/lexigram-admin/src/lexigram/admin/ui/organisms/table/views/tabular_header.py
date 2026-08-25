"""Column-header rendering for TabularView."""

from __future__ import annotations

from typing import Any

from lexigram.ui import Checkbox, el


def render_table_header(
    config: Any,
    state: Any,
    data: list[Any],
    user: Any,
    resource_name: str | None,
) -> Any:
    """Render the sticky ``thead`` row with bulk, expand and column cells."""
    current_sort = state.sort_by
    current_order = state.sort_order

    # 1. Header Logic
    header_cells = []
    left_offset = 0

    # Checkbox header
    if config.resource_prefix and config.bulk_actions:
        all_ids = []
        for item in data:
            item_id: Any = ""
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
            getattr(col, "_pinned", None) == "left" for col in config.columns
        )
        style = ""
        cls = "px-6 py-3 text-left w-12 sticky top-0 z-30 bg-muted dark:bg-background"
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
    elif config.resource_prefix:
        pass

    # Spacer for expandable
    if config.expandable_relationship:
        header_cells.append(
            el(
                "th",
                "",
                class_="px-6 py-3 text-left w-12 sticky top-0 z-20 bg-muted dark:bg-background",
            ),
        )

    for col in config.columns:
        if not col.is_visible(user=user, resource_name=resource_name):
            continue
        header_th = col.render_header(
            current_sort,
            current_order,
            state=state,
            resource_prefix=getattr(config, "resource_prefix", ""),
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
            if getattr(config, "reorderable_columns", False):
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

    if config.resource_prefix:
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
