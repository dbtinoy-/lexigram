"""Pivot data field for editable pivot columns in relation managers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lexigram.admin.schema.base import SchemaField
from lexigram.admin.schema.exceptions import FieldError
from lexigram.result import Ok, Result
from lexigram.ui import Element, raw


@dataclass(frozen=True, kw_only=True)
class PivotColumn:
    """Configuration for a single pivot column."""

    name: str
    label: str
    field_type: str = "text"
    required: bool = False
    default: str = ""


class PivotDataField(SchemaField):
    """Editable pivot columns displayed inline in a relation manager.

    Renders form fields for each pivot column.
    """

    def __init__(
        self,
        name: str,
        *,
        pivot_columns: list[PivotColumn] | None = None,
        related_id: str = "",
        **kwargs: Any,
    ) -> None:
        super().__init__(name=name, **kwargs)
        self._pivot_columns = pivot_columns or []
        self._related_id = related_id

    @property
    def pivot_columns(self) -> list[PivotColumn]:
        return self._pivot_columns

    def render_form(
        self, value: dict[str, Any] | None, *, errors: list[str] | None = None
    ) -> Element:
        data = value or {}

        children: list[Element] = []
        for col in self.pivot_columns:
            current = data.get(col.name, col.default)
            input_html = self._build_pivot_input(col, current)

            children.append(
                Element(
                    "div",
                    Element(
                        "label",
                        col.label,
                        class_="text-xs font-medium text-muted-foreground w-24",
                    ),
                    raw(input_html),
                    class_="flex items-center gap-2 mb-2",
                )
            )

        return Element(
            "div",
            *children,
            class_="pivot-data-fields",
        )

    def _build_pivot_input(self, col: PivotColumn, value: str) -> str:
        attrs = f'name="pivot_{col.name}" '
        if col.field_type == "checkbox":
            checked = "checked" if value else ""
            return f'<input type="checkbox" {attrs} {checked} class="rounded border-border text-primary-600" />'
        if col.field_type == "select":
            return f'<select {attrs} class="px-2 py-1 text-sm border rounded">{value}</select>'
        return f'<input type="{col.field_type}" {attrs} value="{value}" class="px-2 py-1 text-sm border rounded w-full" />'

    def render_column(self, record: Any, value: dict[str, Any] | None) -> Element:
        if value is None:
            return Element("span", "\u2014", class_="text-muted")
        parts = ", ".join(f"{k}={v}" for k, v in value.items())
        return Element("span", parts, class_="text-sm text-muted-foreground")

    def from_form(self, raw: str | None) -> Result[dict[str, Any] | None, FieldError]:
        if raw is None:
            return Ok(None)
        if isinstance(raw, dict):
            return Ok(dict(raw))
        return Ok({})

    def to_form(self, value: dict[str, Any] | None) -> str:
        return ""


class PivotTable:
    """Table organism showing related records with inline pivot editing.

    Renders a table where each row has the related record label,
    editable pivot columns, and detach action.
    """

    def __init__(
        self,
        pivot_columns: list[PivotColumn],
        rows: list[dict[str, Any]] | None = None,
    ):
        self.pivot_columns = pivot_columns
        self.rows = rows or []

    def render(self, resource_name: str = "", parent_id: str = "") -> str:
        rel_name = "pivot"

        header_cols = "".join(
            f'<th class="px-4 py-2 text-left text-xs font-medium text-muted-foreground uppercase">{c.label}</th>'
            for c in self.pivot_columns
        )

        rows_html = ""
        for row in self.rows:
            related_id = row.get("id", "")
            label = row.get("label", related_id)

            pivot_cells = ""
            for col in self.pivot_columns:
                value = row.get("pivot", {}).get(col.name, col.default)
                pivot_cells += f"""<td class="px-4 py-2">
                    <input type="text" class="px-2 py-1 text-sm border rounded w-full"
                           value="{value}" name="pivot_{col.name}"
                           hx-post="/admin/{resource_name}/{parent_id}/relations/{rel_name}/pivot/{related_id}"
                           hx-trigger="change" hx-swap="none" />
                </td>"""

            rows_html += f"""<tr>
                <td class="px-4 py-2 text-sm font-medium text-foreground">{label}</td>
                {pivot_cells}
                <td class="px-4 py-2 text-sm">
                    <button class="text-destructive hover:text-destructive/90 text-sm"
                            hx-delete="/admin/{resource_name}/{parent_id}/relations/{rel_name}/{related_id}"
                            hx-confirm="Detach this record?"
                            hx-target="closest tr" hx-swap="outerHTML">Detach</button>
                </td>
            </tr>"""

        return f"""<table class="min-w-full divide-y divide-border">
            <thead class="bg-muted dark:bg-card">
                <tr>
                    <th class="px-4 py-2 text-left text-xs font-medium text-muted-foreground uppercase">Record</th>
                    {header_cols}
                    <th class="px-4 py-2 text-left text-xs font-medium text-muted-foreground uppercase">Actions</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-border">{rows_html}</tbody>
        </table>"""
