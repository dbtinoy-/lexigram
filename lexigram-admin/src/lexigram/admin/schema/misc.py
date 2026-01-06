from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from lexigram.admin.schema.base import SchemaField
from lexigram.admin.schema.boolean import BooleanField
from lexigram.admin.schema.exceptions import FieldError
from lexigram.result import Err, Ok, Result
from lexigram.serialization import dumps_str, loads_str
from lexigram.ui import (
    ColorPicker,
    Element,
    Rating,
    Switch,
    TagsInput,
)
from lexigram.ui import (
    KeyValueField as KeyValueWidget,
)


@dataclass(frozen=True, kw_only=True)
class ToggleField(BooleanField):
    """A boolean toggle field that always renders as a Switch."""

    def render_form(
        self, value: bool | None, *, errors: list[str] | None = None
    ) -> Element:
        kwargs: dict[str, Any] = {
            "name": self.name,
            "value": value if value is not None else False,
        }
        if self.label is not None:
            kwargs["label"] = self.label
        else:
            kwargs["label"] = ""
        if errors:
            kwargs["error"] = errors[0]
        return Switch(**kwargs).render()


@dataclass(frozen=True, kw_only=True)
class ColorField(SchemaField[str]):
    """A color picker field for hex color values."""

    def render_form(
        self, value: str | None, *, errors: list[str] | None = None
    ) -> Element:
        kwargs: dict[str, Any] = {
            "name": self.name,
            "value": value if value is not None else "#000000",
        }
        if self.label is not None:
            kwargs["label"] = self.label
        if errors:
            kwargs["error"] = errors[0]
        return ColorPicker(**kwargs).render()

    def render_column(self, record: Any, value: str | None) -> Element:
        if value is None:
            return Element("span", "\u2014", class_="text-muted")
        swatch = Element(
            "span",
            style=(
                f"background-color: {value};"
                " display: inline-block;"
                " width: 16px; height: 16px;"
                " border-radius: 3px;"
                " margin-right: 6px;"
                " vertical-align: middle;"
                " border: 1px solid #ccc;"
            ),
        )
        return Element("span", swatch, value)

    def from_form(self, raw: str | None) -> Result[str | None, FieldError]:
        if raw is None:
            return Ok(None)
        stripped = raw.strip()
        if not stripped:
            if self.nullable:
                return Ok(None)
            return Err(FieldError("Invalid color"))
        if re.match(r"^#[0-9a-fA-F]{6}$", stripped):
            return Ok(stripped)
        return Err(FieldError("Invalid color format. Must be hex like #ff0000"))

    def to_form(self, value: str | None) -> str:
        return "" if value is None else value


@dataclass(frozen=True, kw_only=True)
class RatingField(SchemaField[int]):
    """A star rating field (1-5)."""

    def render_form(
        self, value: int | None, *, errors: list[str] | None = None
    ) -> Element:
        kwargs: dict[str, Any] = {
            "name": self.name,
            "value": value if value is not None else 0,
        }
        if self.label is not None:
            kwargs["label"] = self.label
        if errors:
            kwargs["error"] = errors[0]
        return Rating(**kwargs).render()

    def render_column(self, record: Any, value: int | None) -> Element:
        if value is None:
            return Element("span", "\u2014", class_="text-muted")
        stars = "\u2605" * value + "\u2606" * (5 - value)
        return Element("span", stars, class_="text-yellow-500")

    def from_form(self, raw: str | None) -> Result[int | None, FieldError]:
        if raw is None:
            return Ok(None)
        stripped = raw.strip()
        if not stripped:
            if self.nullable:
                return Ok(None)
            return Err(FieldError("Invalid rating"))
        try:
            val = int(stripped)
        except ValueError:
            return Err(FieldError("Must be a number between 1 and 5"))
        if val < 1 or val > 5:
            return Err(FieldError("Rating must be between 1 and 5"))
        return Ok(val)

    def to_form(self, value: int | None) -> str:
        return "" if value is None else str(value)


@dataclass(frozen=True, kw_only=True)
class TagsField(SchemaField[list[str]]):
    """A tags input field for comma-separated or JSON array values."""

    def render_form(
        self, value: list[str] | None, *, errors: list[str] | None = None
    ) -> Element:
        kwargs: dict[str, Any] = {"name": self.name}
        if value is not None:
            kwargs["value"] = value
        if self.label is not None:
            kwargs["label"] = self.label
        if self.placeholder is not None:
            kwargs["placeholder"] = self.placeholder
        if errors:
            kwargs["error"] = errors[0]
        return TagsInput(**kwargs).render()

    def render_column(self, record: Any, value: list[str] | None) -> Element:
        if value is None or len(value) == 0:
            return Element("span", "\u2014", class_="text-muted")
        tags = [
            Element(
                "span",
                tag,
                class_="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-primary-100 text-primary-800 mr-1",
            )
            for tag in value
        ]
        return Element("span", *tags)

    def from_form(self, raw: str | None) -> Result[list[str] | None, FieldError]:
        if raw is None:
            return Ok(None)
        stripped = raw.strip()
        if not stripped:
            if self.nullable:
                return Ok(None)
            return Ok([])
        if stripped.startswith("["):
            try:
                parsed = loads_str(stripped)
                if isinstance(parsed, list):
                    return Ok([str(t).strip() for t in parsed if str(t).strip()])
            except ValueError:
                pass
        return Ok([t.strip() for t in stripped.split(",") if t.strip()])

    def to_form(self, value: list[str] | None) -> str:
        return "" if value is None else ",".join(value)


@dataclass(frozen=True, kw_only=True)
class KeyValueField(SchemaField[dict[str, str]]):
    """A key-value field backed by JSON editing."""

    def render_form(
        self, value: dict[str, str] | None, *, errors: list[str] | None = None
    ) -> Element:
        kwargs: dict[str, Any] = {"name": self.name}
        if value is not None:
            kwargs["value"] = dict(value)
        if self.label is not None:
            kwargs["label"] = self.label
        if errors:
            kwargs["error"] = errors[0]
        return KeyValueWidget(**kwargs).render()

    def render_column(self, record: Any, value: dict[str, str] | None) -> Element:
        if value is None or len(value) == 0:
            return Element("span", "\u2014", class_="text-muted")
        rows = [
            Element(
                "tr",
                Element(
                    "td",
                    k,
                    class_="font-medium text-gray-700 dark:text-gray-300 pr-4 py-1 text-sm",
                ),
                Element(
                    "td",
                    v,
                    class_="text-gray-600 dark:text-gray-400 py-1 text-sm",
                ),
            )
            for k, v in value.items()
        ]
        return Element(
            "table",
            Element("tbody", *rows),
            class_="min-w-full",
        )

    def from_form(self, raw: str | None) -> Result[dict[str, str] | None, FieldError]:
        if raw is None:
            return Ok(None)
        stripped = raw.strip()
        if not stripped:
            if self.nullable:
                return Ok(None)
            return Err(FieldError("Invalid JSON"))
        try:
            parsed = loads_str(stripped)
        except ValueError:
            return Err(FieldError("Invalid JSON"))
        if not isinstance(parsed, dict):
            return Err(FieldError("Must be a JSON object"))
        result: dict[str, str] = {}
        for k, v in parsed.items():
            result[str(k)] = str(v)
        return Ok(result)

    def to_form(self, value: dict[str, str] | None) -> str:
        return "" if value is None else dumps_str(value)
