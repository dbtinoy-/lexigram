"""Renderers for date and datetime fields."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from lexigram.admin.resources.field_renderers_common import _atom_args
from lexigram.admin.schema import DateField, DateTimeField, SchemaField
from lexigram.ui import DateInput


def _date_input_value(value: Any) -> str:
    """Normalize a date value to the browser ``date`` input format."""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value or "").strip()
    if "T" in text:
        return text.split("T", 1)[0]
    if " " in text:
        return text.split(" ", 1)[0]
    return text


def _datetime_input_value(value: Any) -> str:
    """Normalize a value to ``datetime-local`` (no timezone or seconds)."""
    if isinstance(value, datetime):
        # datetime-local deliberately carries no offset. Keep the submitted
        # wall-clock value rather than emitting an invalid ``+00:00`` suffix.
        return value.replace(tzinfo=None).isoformat(timespec="minutes")
    if isinstance(value, date):
        return f"{value.isoformat()}T00:00"

    text = str(value or "").strip()
    if not text:
        return ""
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        # Preserve an invalid submitted value for the validation response; it
        # is more useful than silently clearing the user's input.
        return text
    return parsed.replace(tzinfo=None).isoformat(timespec="minutes")


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
        return DateInput(**_atom_args(common_args, _date_input_value(value)))


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
        return DateInput(
            **_atom_args(
                common_args,
                _datetime_input_value(value),
                extra={"input_type": "datetime-local"},
            )
        )
