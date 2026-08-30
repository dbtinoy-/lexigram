from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from lexigram.admin.schema.base import SchemaField
from lexigram.admin.schema.exceptions import FieldError
from lexigram.result import Err, Ok, Result
from lexigram.ui import Element, MultiSelect, Radio, Select, TagsInput


@dataclass(frozen=True, kw_only=True)
class SelectField(SchemaField[str]):
    """A select / dropdown field."""

    options: list[tuple[str, str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        normalized = self._normalize_options(self.options)
        object.__setattr__(self, "options", normalized)

    @staticmethod
    def _normalize_options(
        options: list[tuple[str, str]] | dict[str, str] | list[str],
    ) -> list[tuple[str, str]]:
        if isinstance(options, dict):
            return list(options.items())
        if isinstance(options, list):
            result: list[tuple[str, str]] = []
            for item in options:
                if isinstance(item, tuple):
                    result.append(item)
                else:
                    result.append((item, item))
            return result
        return []

    def _get_label(self, value: str) -> str | None:
        for val, label in self.options:
            if val == value:
                return label
        return None

    def render_form(
        self, value: str | None, *, errors: list[str] | None = None
    ) -> Element:
        kwargs: dict[str, Any] = {
            "name": self.name,
            "choices": self.options,
            "value": value if value is not None else "",
        }
        if self.label is not None:
            kwargs["label"] = self.label
        if errors:
            kwargs["error"] = errors[0]
        if self.readonly:
            kwargs["disabled"] = True
        return Select(**kwargs).render()

    def render_column(self, record: Any, value: str | None) -> Element:
        if value is None:
            return Element("span", "\u2014", class_="text-muted")
        label = self._get_label(value)
        display = label if label is not None else value
        return Element("span", display)

    def render_filter(self, current_value: Any | None = None) -> Element | None:
        return Select(
            name=self.name,
            choices=self.options,
            value=current_value,
        ).render()

    def from_form(self, raw: str | None) -> Result[str | None, FieldError]:
        if raw is None:
            return Ok(None)
        stripped = raw.strip()
        if not stripped:
            if self.nullable:
                return Ok(None)
            return Err(FieldError("Invalid option"))
        if self._get_label(stripped) is None:
            return Err(FieldError("Invalid option"))
        return Ok(stripped)

    def to_form(self, value: str | None) -> str:
        if value is None:
            return ""
        return str(value)


@dataclass(frozen=True, kw_only=True)
class EnumField(SelectField):
    """A select field backed by a Python Enum class.

    Auto-derives options from the enum members and coerces form values
    back to enum members on read.
    """

    enum_cls: type[Enum] | None = None

    def __post_init__(self) -> None:
        if self.enum_cls is not None and not self.options:
            derived = [
                (m.value, m.name.replace("_", " ").title()) for m in self.enum_cls
            ]
            object.__setattr__(self, "options", derived)
        super().__post_init__()

    def _get_enum_member(self, value: str) -> Enum | None:
        if self.enum_cls is None:
            return None
        for m in self.enum_cls:
            if m.value == value:
                return m
        return None

    def from_form(self, raw: str | None) -> Result[Enum | None, FieldError]:  # type: ignore[override]
        result = super().from_form(raw)
        if result.is_err():
            return Err(result.unwrap_err())
        value = result.unwrap()
        if value is None:
            return Ok(None)
        member = self._get_enum_member(value)
        if member is not None:
            return Ok(member)
        return Err(FieldError("Invalid option"))

    def to_form(self, value: Enum | None) -> str:  # type: ignore[override]
        if value is None:
            return ""
        return str(value.value)

    def render_column(self, record: Any, value: Enum | str | None) -> Element:
        if value is None:
            return Element("span", "\u2014", class_="text-muted")
        raw = value.value if isinstance(value, Enum) else value
        label = self._get_label(str(raw))
        display = label if label is not None else raw
        return Element("span", display)

    def render_form(
        self, value: Enum | str | None, *, errors: list[str] | None = None
    ) -> Element:
        raw = value.value if isinstance(value, Enum) else value
        return super().render_form(raw, errors=errors)


@dataclass(frozen=True, kw_only=True)
class MultiSelectField(SelectField):
    """A multi-select field allowing multiple value selection."""

    def render_form(  # type: ignore[override]
        self, value: list[str] | None, *, errors: list[str] | None = None
    ) -> Element:
        # A list annotation does not necessarily have a finite choice set.
        # Use the free-form tags control when options were not configured,
        # rather than rendering an empty select that cannot submit anything.
        if not self.options:
            kwargs: dict[str, Any] = {"name": self.name}
            if value is not None:
                kwargs["value"] = value
            if self.label is not None:
                kwargs["label"] = self.label
            if errors:
                kwargs["error"] = errors[0]
            if self.placeholder is not None:
                kwargs["placeholder"] = self.placeholder
            if self.readonly:
                kwargs["disabled"] = True
            return TagsInput(**kwargs).render()

        kwargs = {
            "name": self.name,
            "choices": self.options,
        }
        if value is not None:
            kwargs["value"] = value
        if self.label is not None:
            kwargs["label"] = self.label
        if errors:
            kwargs["error"] = errors[0]
        if self.placeholder is not None:
            kwargs["placeholder"] = self.placeholder
        if self.readonly:
            kwargs["disabled"] = True
        return MultiSelect(**kwargs).render()

    def render_column(self, record: Any, value: list[str] | None) -> Element:  # type: ignore[override]
        if value is None:
            return Element("span", "\u2014", class_="text-muted")
        labels: list[str] = []
        for v in value:
            label = self._get_label(v)
            labels.append(label if label is not None else v)
        return Element("span", ", ".join(labels))

    def from_form(self, raw: str | None) -> Result[list[str] | None, FieldError]:  # type: ignore[override]
        if raw is None:
            return Ok(None)
        stripped = raw.strip()
        if not stripped:
            if self.nullable:
                return Ok(None)
            return Err(FieldError("Invalid option"))
        values = [v.strip() for v in stripped.split(",") if v.strip()]
        # With no configured options this is a free-form list (the same
        # contract as TagsField). Finite option lists remain strict so invalid
        # submitted values cannot bypass relation/choice validation.
        if not self.options:
            return Ok(values)
        for v in values:
            if self._get_label(v) is None:
                return Err(FieldError(f"Invalid option: {v}"))
        return Ok(values)

    def to_form(self, value: list[str] | None) -> str:  # type: ignore[override]
        if value is None:
            return ""
        return ",".join(str(v) for v in value)

    def render_filter(self, current_value: Any | None = None) -> Element | None:
        if not self.options:
            return None
        return Select(
            name=self.name,
            choices=self.options,
            multiple=True,
            value=current_value,
        ).render()


@dataclass(frozen=True, kw_only=True)
class RadioField(SelectField):
    """A radio button group field for single selection."""

    def render_form(
        self, value: str | None, *, errors: list[str] | None = None
    ) -> Element:
        kwargs: dict[str, Any] = {
            "name": self.name,
            "choices": self.options,
            "value": value if value is not None else "",
        }
        if self.label is not None:
            kwargs["label"] = self.label
        if errors:
            kwargs["error"] = errors[0]
        if self.readonly:
            kwargs["disabled"] = True
        return Radio(**kwargs).render()
