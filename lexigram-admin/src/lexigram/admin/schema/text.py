from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lexigram.admin.schema.base import SchemaField
from lexigram.admin.schema.exceptions import FieldError
from lexigram.result import Ok, Result
from lexigram.ui import Element, TextInput


@dataclass(frozen=True, kw_only=True)
class TextField(SchemaField[str]):
    """A single-line text input field."""

    def render_form(
        self, value: str | None, *, errors: list[str] | None = None
    ) -> Element:
        kwargs: dict[str, Any] = {
            "name": self.name,
            "value": value if value is not None else "",
        }
        if self.placeholder is not None:
            kwargs["placeholder"] = self.placeholder
        if self.label is not None:
            kwargs["label"] = self.label
        if errors:
            kwargs["error"] = errors[0]
        return TextInput(**kwargs).render()

    def render_column(self, record: Any, value: str | None) -> Element:
        if value is None:
            return Element("span", "\u2014", class_="text-muted")
        return Element("span", value)

    def from_form(self, raw: str | None) -> Result[str | None, FieldError]:
        if raw is None:
            return Ok(None)
        stripped = raw.strip()
        if not stripped:
            if self.nullable:
                return Ok(None)
            return Ok("")
        return Ok(stripped)


@dataclass(frozen=True, kw_only=True)
class EmailField(TextField):
    """An email input field.

    Renders an ``<input type="email">`` form control and displays
    the value as a ``mailto:`` link in columns.
    """

    def render_form(
        self, value: str | None, *, errors: list[str] | None = None
    ) -> Element:
        kwargs: dict[str, Any] = {
            "name": self.name,
            "value": value if value is not None else "",
            "input_type": "email",
        }
        if self.placeholder is not None:
            kwargs["placeholder"] = self.placeholder
        if self.label is not None:
            kwargs["label"] = self.label
        if errors:
            kwargs["error"] = errors[0]
        return TextInput(**kwargs).render()

    def render_column(self, record: Any, value: str | None) -> Element:
        if value is None:
            return Element("span", "\u2014", class_="text-muted")
        return Element("a", value, href=f"mailto:{value}")


@dataclass(frozen=True, kw_only=True)
class PasswordField(TextField):
    """A password input field.

    Renders an ``<input type="password">`` form control and masks
    the value in columns.
    """

    def render_form(
        self, value: str | None, *, errors: list[str] | None = None
    ) -> Element:
        kwargs: dict[str, Any] = {
            "name": self.name,
            "value": value if value is not None else "",
            "input_type": "password",
        }
        if self.placeholder is not None:
            kwargs["placeholder"] = self.placeholder
        if self.label is not None:
            kwargs["label"] = self.label
        if errors:
            kwargs["error"] = errors[0]
        return TextInput(**kwargs).render()

    def render_column(self, record: Any, value: str | None) -> Element:
        if value is None:
            return Element("span", "\u2014", class_="text-muted")
        return Element("span", "\u2022\u2022\u2022\u2022\u2022\u2022")


@dataclass(frozen=True, kw_only=True)
class URLField(TextField):
    """A URL input field.

    Renders an ``<input type="url">`` form control and displays
    the value as a clickable link in columns.
    """

    def render_form(
        self, value: str | None, *, errors: list[str] | None = None
    ) -> Element:
        kwargs: dict[str, Any] = {
            "name": self.name,
            "value": value if value is not None else "",
            "input_type": "url",
        }
        if self.placeholder is not None:
            kwargs["placeholder"] = self.placeholder
        if self.label is not None:
            kwargs["label"] = self.label
        if errors:
            kwargs["error"] = errors[0]
        return TextInput(**kwargs).render()

    def render_column(self, record: Any, value: str | None) -> Element:
        if value is None:
            return Element("span", "\u2014", class_="text-muted")
        return Element("a", value, href=value, target="_blank")
