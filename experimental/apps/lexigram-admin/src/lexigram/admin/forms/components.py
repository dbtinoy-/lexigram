"""Unified Form Components.

Includes FormMeta, FormBase, and build_form. The declarative schema layer
(``FormSchema``, ``FormSchemaGenerator``) lives in ``schema_generator`` and
is re-exported here.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from lexigram.admin.forms.builder import Form

from lexigram.admin.exceptions import AdminValidationError
from lexigram.admin.forms.schema_generator import (
    FormSchema as FormSchema,
)
from lexigram.admin.forms.schema_generator import (
    FormSchemaGenerator as FormSchemaGenerator,
)
from lexigram.admin.schema import SchemaField
from lexigram.contracts.exceptions import FieldError
from lexigram.result import Err, Ok, Result
from lexigram.ui import Component, el


class FormMeta(type):
    """Metaclass to collect SchemaField instances from class attributes."""

    def __new__(mcs, name, bases, namespace) -> Any:
        fields: dict[str, SchemaField] = {}
        for base in bases:
            if hasattr(base, "_declared_fields"):
                fields.update(base._declared_fields)
        for key, value in list(namespace.items()):
            if isinstance(value, SchemaField):
                fields[key] = dataclasses.replace(value, name=key)
        namespace["_declared_fields"] = fields
        return super().__new__(mcs, name, bases, namespace)


class FormBase(Component, metaclass=FormMeta):
    """Base form class with lifecycle and rendering support."""

    _declared_fields: ClassVar[dict[str, SchemaField]]

    def __init__(
        self,
        data: dict | None = None,
        initial: dict | None = None,
        action: str | None = None,
        method: str = "POST",
        hx_post: str | None = None,
        hx_target: str | None = None,
        **props: Any,
    ) -> None:
        super().__init__(**props)
        self.data = data or {}
        self.initial = initial or {}
        self.action = action
        self.method = method
        self.hx_post = hx_post
        self.hx_target = hx_target
        self.fields: dict[str, SchemaField] = dict(self._declared_fields)
        self.values: dict[str, Any] = {}
        self.errors: dict[str, list[str]] = {}
        self._initialize_fields()
        if self.data:
            self.is_valid()

    def _initialize_fields(self) -> None:
        for name, field_schema in self._declared_fields.items():
            if name in self.data:
                self.values[name] = self.data[name]
            elif name in self.initial:
                self.values[name] = self.initial[name]
            else:
                self.values[name] = field_schema.default

    def is_valid(self) -> bool:
        self.errors = {}
        is_valid = True
        for name, field_schema in self._declared_fields.items():
            value = self.values.get(name)
            raw = value if value is None or isinstance(value, str) else str(value)
            result = field_schema.from_form(raw)
            if result.is_err():
                error = result.unwrap_err()
                self.errors[name] = [str(error)]
                is_valid = False
                continue
            cleaned = result.unwrap()
            if field_schema.required and (
                cleaned is None or (isinstance(cleaned, str) and not cleaned)
            ):
                self.errors[name] = ["This field is required."]
                is_valid = False
            else:
                self.values[name] = cleaned
        return is_valid

    async def validate(self) -> Result[dict[str, Any], AdminValidationError]:
        """Validate form data, returning a Result.

        Returns:
            Ok containing cleaned data dict on success, or Err containing
            AdminValidationError with per-field FieldError detail on failure.
        """
        if self.is_valid():
            return Ok(self.cleaned_data)
        field_errors = [
            FieldError(field=name, message=msgs[0], code="invalid")
            for name, msgs in self.errors.items()
            if msgs
        ]
        return Err(
            AdminValidationError(
                message="Form validation failed",
                errors=field_errors,
            )
        )

    @property
    def cleaned_data(self) -> dict:
        return dict(self.values)

    def render(self) -> Any:
        from lexigram.ui import Button

        layout = getattr(self, "layout", None)
        if layout:
            if hasattr(layout, "render"):
                form_body = layout.render(self)
            elif isinstance(layout, list):
                form_body = el(
                    "div",
                    *[
                        (n.render(self) if hasattr(n, "render") else str(n))
                        for n in layout
                    ],
                    class_="space-y-6",
                )
            else:
                form_body = str(layout)
        else:
            form_content = [
                field_schema.render_form(self.values.get(name))
                for name, field_schema in self.fields.items()
            ]
            form_body = el("div", *form_content, class_="space-y-4")

        actions = el(
            "div",
            Button("Submit", type="submit", color="primary"),
            class_="flex justify-end pt-4 border-t border-border mt-6",
        )

        attrs = {
            "method": self.method,
            "class": "bg-card p-6 rounded-lg shadow",
        }
        if self.action:
            attrs["action"] = self.action
        if self.hx_post:
            attrs["hx-post"] = self.hx_post
        if self.hx_target:
            attrs["hx-target"] = self.hx_target

        return el("form", form_body, actions, **attrs)


def build_form(**fields) -> Form[Any]:
    """Build a simple form dynamically from keyword field configs."""
    from lexigram.admin.forms.builder import FormBuilder

    builder = FormBuilder.create()
    for name, config in fields.items():
        builder.text(name, label=config.get("label"))
    return builder.build()
