"""Renderers for date and datetime fields."""

from __future__ import annotations

from typing import Any

from lexigram.admin.resources.field_renderers_common import _atom_args
from lexigram.admin.schema import DateField, DateTimeField, SchemaField
from lexigram.ui import DateInput


class DateFieldRenderer:
    """Renderer for date fields."""

    def can_render(self, field_schema: SchemaField) -> bool:
        return isinstance(field_schema, DateField)

    def render_field(
        self,
        field_schema: SchemaField,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        iso_value = value.isoformat() if value is not None else ""
        return DateInput(**_atom_args(common_args, iso_value))


class DateTimeFieldRenderer:
    """Renderer for datetime fields."""

    def can_render(self, field_schema: SchemaField) -> bool:
        return isinstance(field_schema, DateTimeField)

    def render_field(
        self,
        field_schema: SchemaField,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        iso_value = value.isoformat() if value is not None else ""
        return DateInput(**_atom_args(common_args, iso_value))
