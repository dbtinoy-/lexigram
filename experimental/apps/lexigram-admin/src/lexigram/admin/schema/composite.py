from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lexigram.admin.schema.base import SchemaField
from lexigram.admin.schema.exceptions import FieldError
from lexigram.result import Err, Ok, Result
from lexigram.serialization import dumps_str, loads_str
from lexigram.ui import Element, FileUpload, TextArea, is_safe_navigation_url


@dataclass(frozen=True, kw_only=True)
class JsonField(SchemaField[dict | list]):
    """A JSON editor field for dict/list values."""

    def render_form(
        self, value: dict | list | None, *, errors: list[str] | None = None
    ) -> Element:
        kwargs: dict[str, Any] = {"name": self.name, "rows": 8}
        if value is not None:
            kwargs["value"] = dumps_str(value, indent=2)
        if self.label is not None:
            kwargs["label"] = self.label
        if errors:
            kwargs["error"] = errors[0]
        if self.readonly:
            kwargs["disabled"] = True
        return TextArea(**kwargs).render()

    def render_column(self, record: Any, value: dict | list | None) -> Element:
        if value is None:
            return Element("span", "\u2014", class_="text-muted")
        pretty = dumps_str(value, indent=2)
        return Element(
            "pre",
            pretty,
            class_="text-xs text-muted-foreground max-w-md overflow-x-auto",
        )

    def from_form(self, raw: str | None) -> Result[dict | list | None, FieldError]:
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
        if not isinstance(parsed, (dict, list)):
            return Err(FieldError("Must be a JSON object or array"))
        return Ok(parsed)

    def to_form(self, value: dict | list | None) -> str:
        if value is None:
            return ""
        return dumps_str(value)


@dataclass(frozen=True, kw_only=True)
class HiddenField(SchemaField[Any]):
    """A hidden input field for storing values not displayed to the user."""

    def render_form(
        self, value: Any | None, *, errors: list[str] | None = None
    ) -> Element:
        return Element(
            "input",
            type="hidden",
            name=self.name,
            value=value if value is not None else "",
        )

    def render_column(self, record: Any, value: Any | None) -> Element:
        return Element("span", "\u2014", class_="text-muted")

    def from_form(self, raw: str | None) -> Result[Any, FieldError]:
        return Ok(raw)

    def to_form(self, value: Any | None) -> str:
        return "" if value is None else str(value)


@dataclass(frozen=True, kw_only=True)
class FileField(SchemaField[str]):
    """A file upload field."""

    def render_form(
        self, value: str | None, *, errors: list[str] | None = None
    ) -> Element:
        kwargs: dict[str, Any] = {"name": self.name}
        if self.label is not None:
            kwargs["label"] = self.label
        if self.required:
            kwargs["required"] = True
        if errors:
            kwargs["error"] = errors[0]
        if self.readonly:
            kwargs["disabled"] = True
        return FileUpload(**kwargs).render()

    def render_column(self, record: Any, value: str | None) -> Element:
        if value is None:
            return Element("span", "\u2014", class_="text-muted")
        link = (
            Element(
                "a",
                value,
                href=value,
                target="_blank",
                rel="noopener noreferrer",
            )
            if is_safe_navigation_url(value)
            else Element("span", value)
        )
        return Element("span", link, class_="text-primary-600")

    def from_form(self, raw: str | None) -> Result[str | None, FieldError]:
        if raw is None:
            return Ok(None)
        stripped = raw.strip()
        if not stripped:
            if self.nullable:
                return Ok(None)
            return Ok("")
        return Ok(stripped)

    def to_form(self, value: str | None) -> str:
        return "" if value is None else value


@dataclass(frozen=True, kw_only=True)
class ImageField(FileField):
    """An image upload field with thumbnail preview."""

    thumbnail_size: int = 64

    def render_infolist_entry(self, value: Any) -> Any:
        from lexigram.ui import InfolistEntry, InfolistEntryType

        return InfolistEntry(
            name=self.name,
            label=self.label or self.name.replace("_", " ").title(),
            value=value,
            type=InfolistEntryType.IMAGE,
        )

    def render_column(self, record: Any, value: str | None) -> Element:
        if value is None:
            return Element("span", "\u2014", class_="text-muted")
        if not is_safe_navigation_url(value):
            return Element("span", value)
        return Element(
            "img",
            src=value,
            style=(
                f"width: {self.thumbnail_size}px;"
                f" height: {self.thumbnail_size}px;"
                " object-fit: cover;"
                " border-radius: 4px;"
            ),
            alt="",
        )


@dataclass(frozen=True, kw_only=True)
class AvatarField(ImageField):
    """An avatar upload field with circular thumbnail preview."""

    size: int = 40

    def render_column(self, record: Any, value: str | None) -> Element:
        if value is None:
            return Element("span", "\u2014", class_="text-muted")
        if not is_safe_navigation_url(value):
            return Element("span", value)
        return Element(
            "img",
            src=value,
            style=(
                f"width: {self.size}px;"
                f" height: {self.size}px;"
                " border-radius: 50%;"
                " object-fit: cover;"
            ),
            alt="",
        )
