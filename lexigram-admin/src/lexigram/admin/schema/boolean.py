from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lexigram.admin.schema.base import SchemaField
from lexigram.admin.schema.exceptions import FieldError
from lexigram.result import Err, Ok, Result
from lexigram.ui import Element, Switch


@dataclass(frozen=True, kw_only=True)
class BooleanField(SchemaField[bool]):
    """A boolean toggle field rendered as a Switch."""

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

    def render_column(self, record: Any, value: bool | None) -> Element:
        if value is None:
            return Element("span", "\u2014", class_="text-muted")
        if value:
            return Element("span", "\u2713", class_="text-success")
        return Element("span", "\u2717", class_="text-destructive")

    def from_form(self, raw: str | None) -> Result[bool | None, FieldError]:
        if raw is None:
            return Ok(None)
        stripped = raw.strip()
        if not stripped:
            if self.nullable:
                return Ok(None)
            return Err(FieldError("Must be true or false"))
        lower = stripped.lower()
        if lower in ("true", "1", "yes"):
            return Ok(True)
        if lower in ("false", "0", "no"):
            return Ok(False)
        return Err(FieldError("Must be true or false"))

    def to_form(self, value: bool | None) -> str:
        if value is None:
            return ""
        return "true" if value else "false"
