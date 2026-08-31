"""Pivot data field for editable pivot columns in relation managers."""

from __future__ import annotations

from dataclasses import dataclass
import html as _html
import json
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
        # These fragments are inserted via raw() and must therefore escape
        # every dynamic value themselves: record data (``value``) and the
        # declarative field type both cross into attribute/HTML context.
        attrs = f'name="pivot_{_html.escape(col.name, quote=True)}" '
        if col.field_type == "checkbox":
            checked = "checked" if value else ""
            return f'<input type="checkbox" {attrs} {checked} class="rounded border-border text-primary-600" />'
        if col.field_type == "select":
            option_text = _html.escape(str(value))
            return (
                f'<select {attrs} class="px-2 py-1 text-sm border rounded">'
                f"{option_text}</select>"
            )
        field_type = _html.escape(str(col.field_type), quote=True)
        escaped_value = _html.escape(str(value), quote=True)
        return (
            f'<input type="{field_type}" {attrs} value="{escaped_value}" '
            f'class="px-2 py-1 text-sm border rounded w-full" />'
        )

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

    def render(
        self,
        resource_name: str = "",
        parent_id: str = "",
        admin_prefix: str = "/admin",
        csrf_token: str | None = None,
    ) -> str:
        """Render pivot controls using the configured admin mount prefix."""
        rel_name = "pivot"
        prefix = (admin_prefix.rstrip("/") or "/admin")
        safe_resource = _html.escape(str(resource_name), quote=True)
        safe_parent = _html.escape(str(parent_id), quote=True)
        csrf_attr = ""
        if csrf_token:
            csrf_attr = (
                ' hx-headers="'
                + _html.escape(
                    json.dumps({"X-CSRF-Token": str(csrf_token)}),
                    quote=True,
                )
                + '"'
            )

        header_cols = "".join(
            f'<th class="px-4 py-2 text-left text-xs font-medium text-muted-foreground uppercase">'
            f"{_html.escape(str(c.label))}</th>"
            for c in self.pivot_columns
        )

        rows_html = ""
        for row in self.rows:
            related_id = _html.escape(str(row.get("id", "")), quote=True)
            label = _html.escape(str(row.get("label", row.get("id", ""))))

            pivot_cells = ""
            pivot_values = row.get("pivot") or {}
            for col in self.pivot_columns:
                value = pivot_values.get(col.name, col.default)
                safe_name = _html.escape(str(col.name), quote=True)
                safe_value = _html.escape(str(value), quote=True)
                pivot_url = (
                    f"{prefix}/{safe_resource}/{safe_parent}/relations/{rel_name}/"
                    f"pivot/{related_id}"
                )
                pivot_cells += f"""<td class="px-4 py-2">
                    <input type="text" class="px-2 py-1 text-sm border rounded w-full"
                           value="{safe_value}" name="pivot_{safe_name}"
                           hx-post="{pivot_url}"
                           hx-trigger="change" hx-swap="none"{csrf_attr} />
                </td>"""

            detach_url = (
                f"{prefix}/{safe_resource}/{safe_parent}/relations/{rel_name}/{related_id}"
            )
            rows_html += f"""<tr>
                <td class="px-4 py-2 text-sm font-medium text-foreground">{label}</td>
                {pivot_cells}
                <td class="px-4 py-2 text-sm">
                    <button type="button" class="text-destructive hover:text-destructive/90 text-sm"
                            hx-delete="{detach_url}"
                            hx-confirm="Detach this record?"
                            hx-target="closest tr" hx-swap="outerHTML"{csrf_attr}>Detach</button>
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
