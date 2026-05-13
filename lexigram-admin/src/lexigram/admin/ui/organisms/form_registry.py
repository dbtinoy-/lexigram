"""Registry for form field renderers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from lexigram.ui import DateInput, NumberInput, RichSelect, Switch, TextArea, TextInput

if TYPE_CHECKING:
    from lexigram.admin.forms import AbstractField, FieldType


class FormFieldRendererProtocol(Protocol):
    """Protocol for form field renderers."""

    def can_render(self, field_type: FieldType) -> bool: ...
    def render(self, field: AbstractField, current_value: Any) -> Any: ...


class TextAreaRenderer:
    def can_render(self, field_type: FieldType) -> bool:
        from lexigram.admin.forms import FieldType

        return field_type == FieldType.TEXTAREA

    def render(self, field: AbstractField, current_value: Any) -> Any:
        return TextArea(
            name=field.name,
            label=field.label,
            value=str(current_value) if current_value else "",
            placeholder=field.placeholder,
            error=getattr(field, "errors", [None])[0]
            if getattr(field, "errors", [])
            else None,
            rows=4,
            disabled=not getattr(field, "editable", True),
        )


class SelectRenderer:
    def can_render(self, field_type: FieldType) -> bool:
        from lexigram.admin.forms import FieldType

        return field_type == FieldType.SELECT

    def render(self, field: AbstractField, current_value: Any) -> Any:
        options_with_selection = [
            {**opt, "selected": str(current_value) == str(opt["value"])}
            for opt in field.options  # type: ignore[attr-defined]
        ]
        return RichSelect(
            label=field.label,  # type: ignore[arg-type]
            name=field.name,
            options=options_with_selection,
            value=current_value,
            error=getattr(field, "errors", [None])[0]
            if getattr(field, "errors", [])
            else None,
            disabled=not getattr(field, "editable", True),
        )


class CheckboxRenderer:
    def can_render(self, field_type: FieldType) -> bool:
        from lexigram.admin.forms import FieldType

        return field_type == FieldType.CHECKBOX

    def render(self, field: AbstractField, current_value: Any) -> Any:
        return Switch(
            label=field.label,  # type: ignore[arg-type]
            name=field.name,
            value=bool(current_value) if current_value else False,
            description=field.help_text,
            error=getattr(field, "errors", [None])[0]
            if getattr(field, "errors", [])
            else None,
            disabled=not getattr(field, "editable", True),
        )


class BelongsToFormRenderer:
    def can_render(self, field_type: FieldType) -> bool:
        from lexigram.admin.forms import FieldType

        return field_type == FieldType.BELONGS_TO

    def render(self, field: AbstractField, current_value: Any) -> Any:
        from lexigram.ui.atoms.inputs.selection.relational import BelongsTo

        return BelongsTo(
            name=field.name,
            resource=getattr(field, "metadata", {}).get("related_resource", ""),
            value=current_value,
            label=getattr(field, "label", field.name.title()),
        ).render()


class HasManyFormRenderer:
    def can_render(self, field_type: FieldType) -> bool:
        from lexigram.admin.forms import FieldType

        return field_type == FieldType.HAS_MANY

    def render(self, field: AbstractField, current_value: Any) -> Any:
        from lexigram.ui.atoms.inputs.selection.choice import MultiSelect

        choices = [
            (o.get("value"), o.get("label")) for o in getattr(field, "choices", [])
        ]
        return MultiSelect(
            name=field.name,
            choices=choices,
            value=current_value if isinstance(current_value, list) else [],
            label=getattr(field, "label", field.name.title()),
        ).render()


class InputRenderer:
    """Renderer for standard and specific input types."""

    def __init__(self) -> None:
        from lexigram.admin.forms import FieldType

        self.type_map = {
            FieldType.TEXT: (TextInput, "text"),
            FieldType.EMAIL: (TextInput, "email"),
            FieldType.PASSWORD: (TextInput, "password"),
            FieldType.NUMBER: (NumberInput, None),
            FieldType.DATE: (DateInput, None),
        }

    def can_render(self, field_type: FieldType) -> bool:
        return field_type in self.type_map or True  # Fallback

    def render(self, field: AbstractField, current_value: Any) -> Any:
        atom_class, input_type = self.type_map.get(field.type, (TextInput, "text"))  # type: ignore[attr-defined]

        props = {
            "name": field.name,
            "label": field.label,
            "value": str(current_value) if current_value is not None else "",
            "placeholder": field.placeholder,
            "error": field.error,  # type: ignore[attr-defined]
            "disabled": not getattr(field, "editable", True),
        }
        if input_type:
            props["type"] = input_type

        return atom_class(**props)


class FormFieldRegistry:
    """Registry for form field renderers."""

    def __init__(self) -> None:
        self._renderers: list[FormFieldRendererProtocol] = [
            TextAreaRenderer(),
            SelectRenderer(),
            CheckboxRenderer(),
            BelongsToFormRenderer(),
            HasManyFormRenderer(),
            InputRenderer(),  # Catch-all
        ]

    def get_renderer(self, field_type: FieldType) -> FormFieldRendererProtocol:
        for renderer in self._renderers:
            if renderer.can_render(field_type):
                return renderer
        return InputRenderer()


_form_field_registry = FormFieldRegistry()
