"""Renderers for numeric and boolean fields."""

from __future__ import annotations

from typing import Any

from lexigram.admin.resources.field_renderers_common import _atom_args
from lexigram.admin.schema import BooleanField, NumberField, SchemaField
from lexigram.ui import NumberInput, Switch


class NumberFieldRenderer:
    """Renderer for numeric fields."""

    def can_render(self, field_schema: SchemaField) -> bool:
        return isinstance(field_schema, NumberField)

    def render_field(
        self,
        field_schema: SchemaField,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        return NumberInput(**_atom_args(common_args, value))


class BooleanFieldRenderer:
    """Renderer for boolean fields."""

    def can_render(self, field_schema: SchemaField) -> bool:
        return isinstance(field_schema, BooleanField)

    def render_field(
        self,
        field_schema: SchemaField,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        hx_props = {k: v for k, v in common_args.items() if k.startswith("hx_")}
        return Switch(
            label=common_args.get("label") or "",
            name=common_args["name"],
            value=bool(value),
            **hx_props,
        )
