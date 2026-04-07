from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from lexigram.admin.schema.exceptions import FieldError
from lexigram.admin.schema.select import SelectField
from lexigram.result import Err, Ok, Result
from lexigram.ui import BelongsTo, Element, MultiSelect, Select


@dataclass(frozen=True, kw_only=True)
class RelationField(SelectField):
    """Base field for related-record selection.

    Renders a record picker widget (BelongsTo) for selecting a related
    database record.
    """

    resource: str
    searchable: bool = False

    def render_form(
        self, value: str | None, *, errors: list[str] | None = None
    ) -> Element:
        kwargs: dict[str, Any] = {}
        if value is not None:
            kwargs["value"] = value
        if self.label is not None:
            kwargs["label"] = self.label
        if errors:
            kwargs["error"] = errors[0]
        if self.options:
            kwargs["choices"] = self.options
        return BelongsTo(
            name=self.name,
            resource=self.resource,
            searchable=self.searchable,
            **kwargs,
        ).render()

    def from_form(self, raw: str | None) -> Result[str | None, FieldError]:
        if raw is None:
            return Ok(None)
        stripped = raw.strip()
        if not stripped:
            if self.nullable:
                return Ok(None)
            return Err(FieldError("Invalid option"))
        return Ok(stripped)

    def render_column(self, record: Any, value: str | None) -> Element:
        if value is None:
            return Element("span", "\u2014", class_="text-muted")
        return Element("span", value)


@dataclass(frozen=True, kw_only=True)
class BelongsToField(RelationField):
    """A belongs-to relationship field.

    Renders a searchable dropdown or record picker for selecting the
    related record this record belongs to.
    """


@dataclass(frozen=True, kw_only=True)
class HasManyField(RelationField):
    """A has-many relationship field.

    Renders a multi-select widget for picking multiple related records.
    """

    def render_form(  # type: ignore[override]
        self, value: list[str] | None, *, errors: list[str] | None = None
    ) -> Element:
        kwargs: dict[str, Any] = {
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
        return MultiSelect(**kwargs).render()

    def render_column(  # type: ignore[override]
        self, record: Any, value: list[str] | None
    ) -> Element:
        if value is None:
            return Element("span", "\u2014", class_="text-muted")
        count = len(value)
        label = "item" if count == 1 else "items"
        return Element("span", f"{count} {label}")

    def from_form(self, raw: str | None) -> Result[list[str] | None, FieldError]:  # type: ignore[override]
        if raw is None:
            return Ok(None)
        stripped = raw.strip()
        if not stripped:
            if self.nullable:
                return Ok(None)
            return Err(FieldError("Invalid option"))
        values = [v.strip() for v in stripped.split(",") if v.strip()]
        return Ok(values)

    def to_form(self, value: list[str] | None) -> str:  # type: ignore[override]
        if value is None:
            return ""
        return ",".join(str(v) for v in value)


@dataclass(frozen=True, kw_only=True)
class MorphField(RelationField):
    """A polymorphic relation selector field.

    Renders a type selector (which related model type) alongside a
    record search input.
    """

    morph_types: list[tuple[str, str]] = field(default_factory=list)

    def render_form(
        self, value: str | None, *, errors: list[str] | None = None
    ) -> Element:
        type_select = Select(
            name=f"{self.name}_type",
            choices=self.morph_types,
            value=value if value is not None else "",
        ).render()

        record_select = Select(
            name=f"{self.name}_id",
            value=value if value is not None else "",
        ).render()

        return Element("div", type_select, record_select, class_="morph-field")
