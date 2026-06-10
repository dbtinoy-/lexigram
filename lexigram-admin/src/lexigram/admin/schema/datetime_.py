from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any

from lexigram.admin.schema.base import SchemaField
from lexigram.admin.schema.exceptions import FieldError
from lexigram.result import Err, Ok, Result
from lexigram.ui import DateInput, Element, TimePicker


@dataclass(frozen=True, kw_only=True)
class DateField(SchemaField[date]):
    """A date input field."""

    def render_infolist_entry(self, value: Any) -> Any:
        from lexigram.ui import InfolistEntry, InfolistEntryType

        return InfolistEntry(
            name=self.name,
            label=self.label or self.name.replace('_', ' ').title(),
            value=value,
            type=InfolistEntryType.DATE,
        )

    def render_form(
        self, value: date | None, *, errors: list[str] | None = None
    ) -> Element:
        kwargs: dict[str, Any] = {
            "name": self.name,
            "value": value.isoformat() if value is not None else "",
        }
        if self.label is not None:
            kwargs["label"] = self.label
        if errors:
            kwargs["error"] = errors[0]
        if self.readonly:
            kwargs["disabled"] = True
        return DateInput(**kwargs).render()

    def render_column(self, record: Any, value: date | None) -> Element:
        if value is None:
            return Element("span", "\u2014", class_="text-muted")
        return Element("span", value.strftime("%B %d, %Y"))

    def from_form(self, raw: str | None) -> Result[date | None, FieldError]:
        if raw is None:
            return Ok(None)
        stripped = raw.strip()
        if not stripped:
            if self.nullable:
                return Ok(None)
            return Err(FieldError("Must be a valid date"))
        try:
            parsed = date.fromisoformat(stripped)
            return Ok(parsed)
        except (ValueError, TypeError):
            return Err(FieldError("Must be a valid date"))

    def to_form(self, value: date | None) -> str:
        if value is None:
            return ""
        return value.isoformat()


@dataclass(frozen=True, kw_only=True)
class DateTimeField(SchemaField[datetime]):
    """A datetime input field."""

    def render_infolist_entry(self, value: Any) -> Any:
        from lexigram.ui import InfolistEntry, InfolistEntryType

        return InfolistEntry(
            name=self.name,
            label=self.label or self.name.replace('_', ' ').title(),
            value=value,
            type=InfolistEntryType.DATE,
        )

    def render_form(
        self, value: datetime | None, *, errors: list[str] | None = None
    ) -> Element:
        kwargs: dict[str, Any] = {
            "name": self.name,
            "value": value.isoformat() if value is not None else "",
        }
        if self.label is not None:
            kwargs["label"] = self.label
        if errors:
            kwargs["error"] = errors[0]
        if self.readonly:
            kwargs["disabled"] = True
        return DateInput(input_type="datetime-local", **kwargs).render()

    def render_column(self, record: Any, value: datetime | None) -> Element:
        if value is None:
            return Element("span", "\u2014", class_="text-muted")
        return Element("span", value.strftime("%B %d, %Y, %-I:%M %p"))

    def from_form(self, raw: str | None) -> Result[datetime | None, FieldError]:
        if raw is None:
            return Ok(None)
        stripped = raw.strip()
        if not stripped:
            if self.nullable:
                return Ok(None)
            return Err(FieldError("Must be a valid datetime"))
        try:
            parsed = datetime.fromisoformat(stripped)
            return Ok(parsed)
        except (ValueError, TypeError):
            return Err(FieldError("Must be a valid datetime"))

    def to_form(self, value: datetime | None) -> str:
        if value is None:
            return ""
        return value.isoformat()


@dataclass(frozen=True, kw_only=True)
class TimeField(SchemaField[time]):
    """A time input field."""

    def render_form(
        self, value: time | None, *, errors: list[str] | None = None
    ) -> Element:
        kwargs: dict[str, Any] = {
            "name": self.name,
            "value": value.strftime("%H:%M") if value is not None else "",
        }
        if self.label is not None:
            kwargs["label"] = self.label
        if errors:
            kwargs["error"] = errors[0]
        if self.readonly:
            kwargs["disabled"] = True
        return TimePicker(**kwargs).render()

    def render_column(self, record: Any, value: time | None) -> Element:
        if value is None:
            return Element("span", "\u2014", class_="text-muted")
        return Element("span", value.strftime("%-I:%M %p"))

    def from_form(self, raw: str | None) -> Result[time | None, FieldError]:
        if raw is None:
            return Ok(None)
        stripped = raw.strip()
        if not stripped:
            if self.nullable:
                return Ok(None)
            return Err(FieldError("Must be a valid time"))
        try:
            parts = stripped.split(":")
            hour = int(parts[0])
            minute = int(parts[1])
            parsed = time(hour, minute)
            return Ok(parsed)
        except (ValueError, TypeError, IndexError):
            return Err(FieldError("Must be a valid time"))

    def to_form(self, value: time | None) -> str:
        if value is None:
            return ""
        return value.strftime("%H:%M")
