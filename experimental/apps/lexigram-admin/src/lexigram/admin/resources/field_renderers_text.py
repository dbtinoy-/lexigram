"""Renderers for text-like fields (text, area, tags, json, email, password, color)."""

from __future__ import annotations

from typing import Any

from lexigram.admin.resources.field_renderers_common import _atom_args
from lexigram.admin.schema import (
    ColorField,
    EmailField,
    JsonField,
    PasswordField,
    SchemaField,
    TagsField,
    TextAreaField,
    TextField,
)
from lexigram.serialization import dumps_str
from lexigram.ui import TextArea, TextInput


class TextAreaFieldRenderer:
    """Renderer for multi-line text fields."""

    def can_render(self, field_schema: SchemaField) -> bool:
        return isinstance(field_schema, TextAreaField)

    def render_field(
        self,
        field_schema: SchemaField,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        return TextArea(**_atom_args(common_args, value))


class ListFieldRenderer:
    """Renderer for tag-style list fields (comma-joined text area)."""

    def can_render(self, field_schema: SchemaField) -> bool:
        return isinstance(field_schema, TagsField)

    def render_field(
        self,
        field_schema: SchemaField,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        display_value = (
            ", ".join(str(v) for v in value)
            if isinstance(value, list)
            else str(value or "")
        )
        return TextArea(**_atom_args(common_args, display_value))


class JsonFieldRenderer:
    """Renderer for JSON fields."""

    def can_render(self, field_schema: SchemaField) -> bool:
        return isinstance(field_schema, JsonField)

    def render_field(
        self,
        field_schema: SchemaField,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        display_value = dumps_str(value) if value is not None else ""
        args = _atom_args(common_args, display_value, extra={"rows": 8})
        return TextArea(**args)


class EmailFieldRenderer:
    """Renderer for email fields."""

    def can_render(self, field_schema: SchemaField) -> bool:
        return isinstance(field_schema, EmailField)

    def render_field(
        self,
        field_schema: SchemaField,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        return TextInput(
            **_atom_args(common_args, value, extra={"input_type": "email"})
        )


class PasswordFieldRenderer:
    """Renderer for password fields."""

    def can_render(self, field_schema: SchemaField) -> bool:
        return isinstance(field_schema, PasswordField)

    def render_field(
        self,
        field_schema: SchemaField,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        return TextInput(
            **_atom_args(common_args, value, extra={"input_type": "password"})
        )


class ColorFieldRenderer:
    """Renderer for color fields."""

    def can_render(self, field_schema: SchemaField) -> bool:
        return isinstance(field_schema, ColorField)

    def render_field(
        self,
        field_schema: SchemaField,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        return TextInput(
            **_atom_args(common_args, value, extra={"input_type": "color"})
        )


class TextFieldRenderer:
    """Renderer for plain text fields."""

    def can_render(self, field_schema: SchemaField) -> bool:
        return isinstance(field_schema, TextField)

    def render_field(
        self,
        field_schema: SchemaField,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        return TextInput(**_atom_args(common_args, value))


class _SchemaFieldComponent:
    """Component adapter for schema fields without a dedicated renderer."""

    def __init__(
        self,
        field_schema: SchemaField,
        value: Any,
        errors: list[str] | None = None,
    ) -> None:
        self.field_schema = field_schema
        self.value = value
        self.error = errors

    def render(self) -> Any:
        """Use the field's own form widget instead of degrading to text."""
        return self.field_schema.render_form(self.value, errors=self.error)


class DefaultFieldRenderer:
    """Fallback that preserves a custom schema field's widget contract."""

    def can_render(self, field_schema: SchemaField) -> bool:
        return True

    def render_field(
        self,
        field_schema: SchemaField,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        errors = common_args.get("error")
        if not isinstance(errors, list):
            errors = [str(errors)] if errors else None
        return _SchemaFieldComponent(field_schema, value, errors)
