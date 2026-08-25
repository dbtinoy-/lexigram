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
    ):
        self.model = model
        self.fields = {f.name: f for f in fields}
        self.field_list = fields
        self.groups = groups
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

    def _render_field_els(self) -> list[Any]:
        """Render all field elements with current bound values."""
        return [
            el(
                "div",
                field.render_form(self.values.get(name)),
                class_="form-field",
            )
            for name, field in self.fields.items()
        ]

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
                el(
                    "div",
                    *field_els,
                    class_="form-fields",
                    style=f"display:grid;grid-template-columns:repeat({self.columns},1fr);gap:1rem",
                ),
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
                el(
                    "div",
                    *field_els,
                    class_="form-fields",
                    style=f"display:grid;grid-template-columns:repeat({self.columns},1fr);gap:1rem",
                ),
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
