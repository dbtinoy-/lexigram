from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.admin.forms.fields._base import Field
from lexigram.ui import (
    Checkbox,
    DateInput,
    NumberInput,
    Select,
    Switch,
    TextArea,
    TextInput,
)

if TYPE_CHECKING:
    from lexigram.ui.core.base import Component


class TextField(Field):
    """Single-line text input field."""

    def __init__(
        self, label: str | None = None, field_type: str = "text", **kwargs: Any
    ) -> None:
        super().__init__(label=label, **kwargs)
        self.type = field_type

    def render(self, **kwargs) -> Component:
        htmx_attrs = {}
        if self.realtime_validate:
            htmx_attrs.update(
                {
                    "hx_post": f"/admin//forms/validate/{self.name}",
                    "hx_trigger": "blur, change delay:500ms",
                    "hx_target": f"#{self.name}-error",
                    "hx_swap": "innerHTML",
                },
            )
        if self.autocomplete_source:
            htmx_attrs.update(
                {
                    "hx_get": f"/admin//forms/autocomplete/{self.name}",
                    "hx_trigger": "input changed delay:300ms",
                    "hx_target": f"#{self.name}-suggestions",
                    "hx_swap": "innerHTML",
                },
            )
        display_value = self.format_value(self.value)
        if self.mask_pattern and isinstance(display_value, str):
            display_value = self.apply_mask(display_value)
        prefill_attrs = {}
        if self.prefill_from:
            prefill_attrs.update(
                {
                    "data-prefill-from": self.prefill_from,
                    "data-field-name": self.name,
                },
            )
        return TextInput(
            name=self.name,
            value=display_value,
            label=self.label,
            placeholder=self.placeholder,
            type=self.type,
            error=str(self.errors[0]) if self.errors else None,
            required=self.required,
            disabled=self.disabled,
            prefix=self.prefix,
            suffix=self.suffix,
            aria_label=self.aria_label,
            aria_describedby=self.aria_describedby,
            aria_invalid="true" if self.errors else "false",
            aria_errormessage=self.aria_errormessage if self.errors else None,
            **htmx_attrs,
            **prefill_attrs,
            **kwargs,
        )


class IntegerField(Field):
    """Numeric integer input field."""

    def __init__(
        self,
        label: str | None = None,
        min_value: int | None = None,
        max_value: int | None = None,
        step: int | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(label=label, **kwargs)
        self.min = min_value
        self.max = max_value
        self.step = step

    def render(self, **kwargs) -> Component:
        return NumberInput(
            name=self.name,
            value=self.value,
            label=self.label,
            placeholder=self.placeholder,
            error=str(self.errors[0]) if self.errors else None,
            required=self.required,
            disabled=self.disabled,
            min=self.min,
            max=self.max,
            step=self.step,
            **kwargs,
        )


class TextAreaField(Field):
    """Multi-line textarea input field."""

    def __init__(self, label: str | None = None, rows: int = 4, **kwargs: Any) -> None:
        super().__init__(label=label, **kwargs)
        self.rows = rows

    def render(self, **kwargs) -> Component:
        return TextArea(
            name=self.name,
            value=self.value,
            label=self.label,
            placeholder=self.placeholder,
            error=str(self.errors[0]) if self.errors else None,
            required=self.required,
            disabled=self.disabled,
            rows=self.rows,
            **kwargs,
        )


class SelectField(Field):
    """Dropdown select field with single or multiple selection."""

    def __init__(
        self,
        label: str | None = None,
        options: list[tuple[str, str]] | list[str] | None = None,
        multiple: bool = False,
        **kwargs: Any,
    ) -> None:
        if options is None:
            options = []
        super().__init__(label=label, **kwargs)
        self.options: list[tuple[str, str]] = []
        for opt in options:
            if isinstance(opt, (tuple, list)) and len(opt) == 2:
                self.options.append((str(opt[0]), str(opt[1])))
            else:
                self.options.append((str(opt), str(opt)))
        self.multiple = multiple

    def render(self, **kwargs) -> Component:
        return Select(
            name=self.name,
            choices=self.options,
            value=self.value,
            label=self.label,
            error=str(self.errors[0]) if self.errors else None,
            required=self.required,
            disabled=self.disabled,
            multiple=self.multiple,
            **kwargs,
        )


class BooleanField(Field):
    """Boolean checkbox or toggle switch field."""

    def __init__(
        self,
        label: str | None = None,
        widget: str = "checkbox",
        required: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(label=label, required=required, **kwargs)
        self.widget = widget

    def render(self, **kwargs) -> Component:
        if self.widget == "switch":
            return Switch(
                name=self.name,
                value=bool(self.value),
                label=self.label,  # type: ignore[arg-type]
                description=self.help_text,
                error=str(self.errors[0]) if self.errors else None,
                disabled=self.disabled,
                **kwargs,
            )
        return Checkbox(
            name=self.name,
            checked=bool(self.value),
            label=self.label,
            error=str(self.errors[0]) if self.errors else None,
            required=self.required,
            disabled=self.disabled,
            **kwargs,
        )


class DateField(Field):
    """Date picker input field."""

    def render(self, **kwargs) -> Component:
        return DateInput(
            name=self.name,
            value=self.value,
            label=self.label,
            error=str(self.errors[0]) if self.errors else None,
            required=self.required,
            disabled=self.disabled,
            **kwargs,
        )
