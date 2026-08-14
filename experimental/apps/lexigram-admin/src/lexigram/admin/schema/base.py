from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from lexigram.admin.schema.exceptions import FieldError
from lexigram.admin.schema.validators import FieldValidator
from lexigram.result import Ok, Result
from lexigram.ui import Element

T = TypeVar("T")


@dataclass(frozen=True, kw_only=True)
class SchemaField(ABC, Generic[T]):
    """.. stability:: stable"""

    name: str
    label: str | None = None
    help_text: str | None = None
    placeholder: str | None = None

    nullable: bool = True
    readonly: bool = False
    required: bool = False
    sortable: bool = True
    searchable: bool = False
    filterable: bool = True
    visible_in_form: bool = True
    visible_in_list: bool = True
    visible_in_view: bool = True

    validators: list[FieldValidator] = field(default_factory=list)
    default: T | None = None

    @abstractmethod
    def render_form(
        self, value: T | None, *, errors: list[str] | None = None
    ) -> Element:
        """Render this field as a form input."""

    @abstractmethod
    def render_column(self, record: Any, value: T | None) -> Element:
        """Render this field as a table-cell value."""

    def render_infolist_entry(self, value: T | None) -> Any:
        """Render this field as a read-only detail entry."""
        from lexigram.ui import InfolistEntry, InfolistEntryType

        return InfolistEntry(
            name=self.name,
            label=self.label or self.name.replace("_", " ").title(),
            value=value,
            type=InfolistEntryType.TEXT,
        )

    def render_filter(self, current_value: Any | None = None) -> Element | None:
        """Render this field as a filter widget. Return None to opt out."""
        return None

    def get_default(self) -> T | None:
        """Return the default value for this field."""
        return self.default

    def from_form(self, raw: str | None) -> Result[T | None, FieldError]:
        """Coerce a raw form string to the field's Python type."""
        return Ok(raw)  # type: ignore[arg-type]

    def to_form(self, value: T | None) -> str:
        """Coerce the field's Python value to a form-display string."""
        return "" if value is None else str(value)
