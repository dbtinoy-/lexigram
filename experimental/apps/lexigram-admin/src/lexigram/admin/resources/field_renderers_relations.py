"""Renderers for relation fields (has-many, belongs-to, polymorphic)."""

from __future__ import annotations

from typing import Any

from lexigram.admin.resources.field_renderers_common import _atom_args
from lexigram.admin.schema import BelongsToField, HasManyField, MorphField, SchemaField
from lexigram.ui import BelongsTo, MultiSelect, Select


class HasManyFieldRenderer:
    """Renderer for HAS_MANY relation fields."""

    def can_render(self, field_schema: SchemaField) -> bool:
        return isinstance(field_schema, HasManyField)

    def render_field(
        self,
        field_schema: SchemaField,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        if not isinstance(field_schema, HasManyField):
            return None
        choices = field_schema.options or []
        selected = value if isinstance(value, list) else []
        return MultiSelect(
            **_atom_args(common_args, selected, extra={"choices": choices})
        )


class BelongsToFieldRenderer:
    """Renderer for BELONGS_TO relation fields."""

    def can_render(self, field_schema: SchemaField) -> bool:
        return isinstance(field_schema, BelongsToField)

    def render_field(
        self,
        field_schema: SchemaField,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        if not isinstance(field_schema, BelongsToField):
            return None
        return BelongsTo(
            **_atom_args(
                common_args,
                value,
                extra={
                    "resource": field_schema.resource,
                    "choices": field_schema.options or [],
                },
            )
        )


class MorphFieldRenderer:
    """Renderer for polymorphic relation fields."""

    def can_render(self, field_schema: SchemaField) -> bool:
        return isinstance(field_schema, MorphField)

    def render_field(
        self,
        field_schema: SchemaField,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        if not isinstance(field_schema, MorphField):
            return None
        args = _atom_args(
            common_args, value, extra={"choices": field_schema.options or []}
        )
        return Select(**args)
