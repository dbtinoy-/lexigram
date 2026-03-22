"""BelongsToMany field for forms — stores related IDs as JSON array."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lexigram.admin.schema.base import SchemaField
from lexigram.admin.schema.exceptions import FieldError
from lexigram.result import Err, Ok, Result
from lexigram.serialization import dumps_str, loads_str
from lexigram.ui import Element


@dataclass(frozen=True, kw_only=True)
class BelongsToManyField(SchemaField[list[str]]):
    """A multi-select field for belongs-to-many relationships.

    Renders a searchable multi-select interface and stores related
    record IDs as a JSON array.

    Example:
        roles_field = BelongsToManyField(
            name="roles",
            label="Roles",
            searchable=True,
        )
    """

    def render_form(
        self, value: list[str] | None, *, errors: list[str] | None = None
    ) -> Element:
        items = value or []

        x_data = (
            f"{{"
            f"  selectedIds: {dumps_str(items)},"
            f"  searchQuery: '',"
            f"  isOpen: false,"
            f"  toggleId(id) {{"
            f"    let idx = this.selectedIds.indexOf(id);"
            f"    if(idx === -1) {{ this.selectedIds.push(id); }}"
            f"    else {{ this.selectedIds.splice(idx, 1); }}"
            f"  }},"
            f"  get serializedIds() {{ return JSON.stringify(this.selectedIds); }},"
            f"}}"
        )

        hidden = Element(
            "input",
            type="hidden",
            name=self.name,
            **{":value": "serializedIds"},
        )

        selected_display = Element(
            "div",
            **{"x-text": "`${selectedIds.length} selected`"},
            class_="text-sm text-muted-foreground mb-2",
        )

        content = Element(
            "div",
            selected_display,
            hidden,
            **{"x-data": x_data},
            class_="space-y-2",
        )

        if self.label:
            return Element(
                "div",
                Element(
                    "label",
                    self.label,
                    class_="block text-sm font-medium text-foreground mb-1",
                ),
                content,
                (
                    Element(
                        "p",
                        errors[0],
                        id=f"{self.name}-error",
                        class_="mt-2 text-sm text-destructive",
                    )
                    if errors
                    else ""
                ),
                class_="mb-6",
            )

        return content

    def render_column(self, record: Any, value: list[str] | None) -> Element:
        if value is None or not value:
            return Element("span", "\u2014", class_="text-muted")
        count = len(value)
        label = "relation" if count == 1 else "relations"
        return Element(
            "span",
            f"{count} {label}",
            class_="text-sm text-muted-foreground",
        )

    def from_form(self, raw: str | None) -> Result[list[str] | None, FieldError]:
        if raw is None:
            return Ok(None)
        stripped = raw.strip()
        if not stripped:
            if self.nullable:
                return Ok(None)
            return Err(FieldError("Invalid JSON array"))
        try:
            parsed = loads_str(stripped)
        except ValueError:
            return Err(FieldError("Invalid JSON array"))
        if not isinstance(parsed, list):
            return Err(FieldError("Must be a JSON array"))
        validated = [str(x) for x in parsed if x is not None or str(x).strip()]
        return Ok(validated)

    def to_form(self, value: list[str] | None) -> str:
        return "" if value is None else dumps_str(value)
