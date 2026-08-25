"""Renderers for single- and multi-choice selection fields."""

from __future__ import annotations

from typing import Any

from lexigram.admin.resources.field_renderers_common import _atom_args
from lexigram.admin.schema import MultiSelectField, SchemaField, SelectField
from lexigram.ui import MultiSelect, Select


class MultiSelectFieldRenderer:
    """Renderer for multi-select fields."""

    def can_render(self, field_schema: SchemaField) -> bool:
        return isinstance(field_schema, MultiSelectField)

    def render_field(
        self,
        field_schema: SchemaField,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        if not isinstance(field_schema, MultiSelectField):
            return None
        choices = field_schema.options or []
        selected = value if isinstance(value, list) else []
        return MultiSelect(
            **_atom_args(common_args, selected, extra={"choices": choices})
        )


class SelectFieldRenderer:
    """Renderer for select fields."""

    def can_render(self, field_schema: SchemaField) -> bool:
        return isinstance(field_schema, SelectField)

    def render_field(
        self,
        field_schema: SchemaField,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        if not isinstance(field_schema, SelectField):
            return None
        args = _atom_args(
            common_args, value, extra={"choices": field_schema.options or []}
        )
        return Select(**args)
