"""Footer summary rendering for TabularView."""

from __future__ import annotations

from typing import Any

from lexigram.admin.ui.organisms.table.views.summarizers import compute_summaries
from lexigram.ui import el


def effective_summary(
    data: list[Any],
    columns: list[Any],
    summary: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Resolve footer summaries: explicit summary or per-column aggregates."""
    if summary:
        return summary
    computed = compute_summaries(data, columns)
    return computed or None


def render_table_footer(config: Any, summary: dict[str, Any] | None) -> Any:
    """Render the sticky ``tfoot`` summary row."""
    summary_cells = []
    left_offset = 0

    # Checkbox column
    if config.resource_prefix and config.bulk_actions:
        is_pinned = any(
            getattr(col, "_pinned", None) == "left" for col in config.columns
        )
        cls = "px-6 py-3 sticky bottom-0 z-30 bg-muted dark:bg-background border-t border-border"
        style = ""
        if is_pinned:
            style = f"left: {left_offset}px"
            cls += " border-r"
            left_offset += 48
        summary_cells.append(el("td", "", class_=cls, style=style))

    # Expandable spacer
    if config.expandable_relationship:
        summary_cells.append(
            el(
                "td",
                "",
                class_="px-6 py-3 sticky bottom-0 z-20 bg-muted dark:bg-background border-t border-border",
            ),
        )

    # Data columns
    for col in config.columns:
        val = summary.get(col.name, "") if summary else ""
        cls = "px-6 py-3 text-sm font-bold text-foreground sticky bottom-0 z-20 bg-muted dark:bg-background border-t border-border"
        style = ""

        if getattr(col, "_pinned", None) == "left":
            cls += " sticky left-0 z-30 border-r"
            style = f"left: {left_offset}px"
            left_offset += getattr(col, "_width", None) or 150

        summary_cells.append(el("td", str(val), class_=cls, style=style))

    # Actions column
    if config.resource_prefix:
        summary_cells.append(
            el(
                "td",
                "",
                class_="px-6 py-3 sticky bottom-0 z-20 bg-muted dark:bg-background border-t border-border",
            ),
        )

    return el("tfoot", el("tr", *summary_cells, style="height: 50px;"))
