from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lexigram.admin.schema.base import SchemaField
from lexigram.admin.schema.exceptions import FieldError
from lexigram.result import Err, Ok, Result
from lexigram.ui import Element, NumberInput

CURRENCY_SYMBOLS: dict[str, str] = {
    "USD": "$",
    "EUR": "\u20ac",
    "GBP": "\u00a3",
    "JPY": "\u00a5",
    "CAD": "$",
    "AUD": "$",
    "CHF": "CHF",
    "CNY": "\u00a5",
    "SEK": "kr",
    "NOK": "kr",
}


@dataclass(frozen=True, kw_only=True)
class NumberField(SchemaField[int | float]):
    """A numeric input field supporting integers and floats."""

    def render_form(
        self, value: float | None, *, errors: list[str] | None = None
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
        return NumberInput(**kwargs).render()

    def render_column(self, record: Any, value: float | None) -> Element:
        if value is None:
            return Element("span", "\u2014", class_="text-muted")
        return Element("span", str(value))

    def from_form(self, raw: str | None) -> Result[int | float | None, FieldError]:
        if raw is None:
            return Ok(None)
        stripped = raw.strip()
        if not stripped:
            if self.nullable:
                return Ok(None)
            return Err(FieldError("Must be a number"))
        try:
            if "." in stripped:
                return Ok(float(stripped))
            return Ok(int(stripped))
        except (ValueError, TypeError):
            return Err(FieldError("Must be a number"))

    def to_form(self, value: float | None) -> str:
        if value is None:
            return ""
        return str(value)


@dataclass(frozen=True, kw_only=True)
class IntegerField(NumberField):
    """An integer-only input field."""

    def from_form(self, raw: str | None) -> Result[int | None, FieldError]:  # type: ignore[override]
        if raw is None:
            return Ok(None)
        stripped = raw.strip()
        if not stripped:
            if self.nullable:
                return Ok(None)
            return Err(FieldError("Must be an integer"))
        try:
            if "." in stripped:
                return Err(FieldError("Must be an integer"))
            return Ok(int(stripped))
        except (ValueError, TypeError):
            return Err(FieldError("Must be an integer"))

    def render_column(self, record: Any, value: float | None) -> Element:
        if value is None:
            return Element("span", "\u2014", class_="text-muted")
        return Element("span", str(int(value)))


@dataclass(frozen=True, kw_only=True)
class FloatField(NumberField):
    """A float-only input field."""

    def from_form(self, raw: str | None) -> Result[float | None, FieldError]:
        if raw is None:
            return Ok(None)
        stripped = raw.strip()
        if not stripped:
            if self.nullable:
                return Ok(None)
            return Err(FieldError("Must be a number"))
        try:
            return Ok(float(stripped))
        except (ValueError, TypeError):
            return Err(FieldError("Must be a number"))


@dataclass(frozen=True, kw_only=True)
class CurrencyField(NumberField):
    """A currency input field with configurable currency symbol."""

    currency: str = "USD"

    def render_column(self, record: Any, value: float | None) -> Element:
        if value is None:
            return Element("span", "\u2014", class_="text-muted")
        symbol = CURRENCY_SYMBOLS.get(self.currency, self.currency)
        return Element("span", f"{symbol}{float(value):.2f}")

    def from_form(self, raw: str | None) -> Result[float | None, FieldError]:
        if raw is None:
            return Ok(None)
        stripped = raw.strip()
        if not stripped:
            if self.nullable:
                return Ok(None)
            return Err(FieldError("Must be a number"))
        try:
            return Ok(float(stripped))
        except (ValueError, TypeError):
            return Err(FieldError("Must be a number"))
