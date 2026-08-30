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
        if isinstance(value, str):
            value = value.strip().lower() in {"true", "1", "yes", "on"}
        elif isinstance(value, (list, tuple)):
            value = any(
                str(item).strip().lower() in {"true", "1", "yes", "on"}
                for item in value
            )
        else:
            value = bool(value)
        error = common_args.get("error")
        if isinstance(error, list):
            error = error[0] if error else None
        return Switch(
            label=common_args.get("label") or "",
            name=common_args["name"],
            value=bool(value),
            error=error,
            disabled=bool(common_args.get("readonly", common_args.get("disabled", False))),
            **hx_props,
        )
