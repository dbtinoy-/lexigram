"""Built form object and validation result for the admin form system.

``Form`` is produced by ``FormBuilder.build()``; ``FormResult`` carries the
outcome of ``Form.validate()``.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dataclass_field
from typing import Any, Generic, TypeVar

from lexigram.admin.schema import SchemaField
from lexigram.domain import DomainModel
from lexigram.ui import el, render_to_string

T = TypeVar("T", bound=DomainModel)


@dataclass
class FormResult(Generic[T]):
    """Result of form validation."""

    success: bool
    data: T | None = None
    errors: dict[str, list[str]] = dataclass_field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        return self.success and not self.errors


class Form(Generic[T]):
    """A built form ready for rendering and validation."""

    def __init__(
        self,
        model: type[T],
        fields: list[SchemaField],
        groups: dict[str, list[str]],
        layout: str,
        columns: int,
        submit_label: str,
        cancel_url: str | None,
        group_labels: dict[str, str] | None = None,
    ):
        self.model = model
        self.fields = {f.name: f for f in fields}
        self.field_list = fields
        self.groups = groups
        self.group_labels = group_labels or {}
        self.layout = layout
        self.columns = columns
        self.submit_label = submit_label
        self.cancel_url = cancel_url
        self.values: dict[str, Any] = {}
        self.errors: dict[str, list[str]] = {}

    def bind(self, data: dict[str, Any]) -> Form[T]:
        """Bind data to form values."""
        for name in self.fields:
            if name in data:
                self.values[name] = data[name]
        return self

    async def validate(self, data: dict[str, Any]) -> FormResult[T]:
        """Validate form data against model."""
        errors: dict[str, list[str]] = {}
        cleaned: dict[str, Any] = {}

        # Run field-level validation first
        for name, field in self.fields.items():
            if name not in data:
                continue
            raw = data.get(name)
            raw = raw if raw is None or isinstance(raw, str) else str(raw)
            result = field.from_form(raw)
            if result.is_err():
                message = str(result.unwrap_err())
                errors.setdefault(name, []).append(message)
                self.errors[name] = [message]
            else:
                value = result.unwrap()
                if field.required and (
                    value is None or (isinstance(value, str) and not value)
                ):
                    message = "This field is required."
                    errors.setdefault(name, []).append(message)
                    self.errors[name] = [message]
                else:
                    cleaned[name] = value

        # If field validation passed, try Pydantic model validation
        if not errors and self.model is not None:
            try:
                instance = self.model.model_validate(cleaned)
                return FormResult(success=True, data=instance)
            except (ValueError, TypeError, AttributeError) as e:
                if hasattr(e, "errors"):
                    for error in e.errors():
                        field_name = (
                            str(error["loc"][0]) if error["loc"] else "__root__"
                        )
                        message = error["msg"]
                        errors.setdefault(field_name, []).append(message)
                        self.errors[field_name] = [message]
                else:
                    message = str(e)
                    errors.setdefault("__root__", []).append(message)
                    self.errors["__root__"] = [message]

        return FormResult(success=False, errors=errors)

    def _render_field_el(self, name: str) -> Any:
        """Render a single field with its bound value and errors."""
        return el(
            "div",
            self.fields[name].render_form(
                self.values.get(name),
                errors=self.errors.get(name),
            ),
            class_="form-field",
        )

    def _render_field_els(self) -> list[Any]:
        """Render fields as flat rows, or grouped sections when declared.

        When ``groups`` is non-empty each group renders as a titled section
        containing its fields in declaration order; fields not assigned to a
        group render after the sections so nothing is dropped.
        """
        if not self.groups:
            return [
                self._render_field_el(name)
                for name, field in self.fields.items()
                if field.visible_in_form
            ]

        assigned: set[str] = set()
        body: list[Any] = []
        grid_style = (
            f"display:grid;grid-template-columns:repeat({self.columns},1fr);gap:1rem"
        )
        for group_name, field_names in self.groups.items():
            group_fields = [
                self._render_field_el(name)
                for name in field_names
                if name in self.fields and self.fields[name].visible_in_form
            ]
            if not group_fields:
                continue
            assigned.update(
                name
                for name in field_names
                if name in self.fields and self.fields[name].visible_in_form
            )
            body.append(
                el(
                    "div",
                    el(
                        "h3",
                        self.group_labels.get(group_name)
                        or group_name.replace("_", " ").title(),
                        class_="text-lg font-medium text-foreground",
                    ),
                    el(
                        "div",
                        *group_fields,
                        class_="form-group-fields",
                        style=grid_style,
                    ),
                    class_="form-group",
                )
            )

        leftovers = [
            self._render_field_el(name)
            for name, field in self.fields.items()
            if name not in assigned and field.visible_in_form
        ]
        if leftovers:
            body.extend(leftovers)
        return body

    def _fields_container_el(self, field_els: list[Any]) -> Any:
        """Wrap rendered fields: grid when flat, stacked when grouped.

        Grouped forms render each group as its own grid (see
        :meth:`_render_field_els`); the outer container stays stacked so
        sections never sit side-by-side.
        """
        if self.groups:
            return el("div", *field_els, class_="form-fields space-y-6")
        return el(
            "div",
            *field_els,
            class_="form-fields",
            style=(
                f"display:grid;grid-template-columns:repeat({self.columns},1fr);"
                "gap:1rem"
            ),
        )

    def render_html(self, action: str, method: str = "POST") -> str:
        """Render form as HTML."""
        field_els = self._render_field_els()
        btns: list[Any] = [
            el("button", self.submit_label, type="submit", class_="btn btn-primary")
        ]
        if self.cancel_url:
            btns.append(
                el("a", "Cancel", href=self.cancel_url, class_="btn btn-secondary")
            )
        return render_to_string(
            el(
                "form",
                self._fields_container_el(field_els),
                el("div", *btns, class_="form-actions", style="margin-top:1.5rem"),
                action=action,
                method=method,
                class_=f"admin-form layout-{self.layout}",
            )
        )

    def render_htmx(
        self,
        action: str,
        target: str = "#form-result",
        swap: str = "innerHTML",
    ) -> str:
        """Render form with HTMX attributes."""
        field_els = self._render_field_els()
        btns: list[Any] = [
            el("button", self.submit_label, type="submit", class_="btn btn-primary")
        ]
        if self.cancel_url:
            btns.append(
                el("a", "Cancel", href=self.cancel_url, class_="btn btn-secondary")
            )
        spinner_id = target.lstrip("#") + "-spinner"
        return render_to_string(
            el(
                "form",
                el("div", "Saving...", id=spinner_id, class_="htmx-indicator"),
                self._fields_container_el(field_els),
                el("div", *btns, class_="form-actions", style="margin-top:1.5rem"),
                **{
                    "hx-post": action,
                    "hx-target": target,
                    "hx-swap": swap,
                    "hx-indicator": "#form-spinner",
                    "class": f"admin-form layout-{self.layout}",
                },
            )
        )
