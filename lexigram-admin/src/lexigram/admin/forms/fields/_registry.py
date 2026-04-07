from __future__ import annotations

from typing import Any

from lexigram.admin.forms.fields._advanced import (
    ColorField,
    KeyValueField,
    MarkdownField,
    RichTextField,
    TagsField,
)
from lexigram.admin.forms.fields._base import FieldType
from lexigram.admin.forms.fields._text import (
    BooleanField,
    DateField,
    IntegerField,
    SelectField,
    TextAreaField,
    TextField,
)


class FieldRegistry:
    """Registry for form field types and their corresponding UI widgets."""

    _registry: dict[FieldType, Any] = {}
    _custom_widgets: dict[str, Any] = {}

    @classmethod
    def register(cls, field_type: FieldType, widget: Any) -> None:
        cls._registry[field_type] = widget

    @classmethod
    def register_custom(cls, name: str, widget: Any) -> None:
        cls._custom_widgets[name] = widget

    @classmethod
    def get_widget(
        cls,
        field_type: FieldType,
        custom_name: str | None = None,
    ) -> Any:
        if custom_name and custom_name in cls._custom_widgets:
            return cls._custom_widgets[custom_name]
        return cls._registry.get(field_type)

    @classmethod
    def has_type(cls, field_type: FieldType) -> bool:
        return field_type in cls._registry


FieldRegistry.register(FieldType.TEXT, TextField)
FieldRegistry.register(FieldType.NUMBER, IntegerField)
FieldRegistry.register(FieldType.EMAIL, TextField)
FieldRegistry.register(FieldType.PASSWORD, TextField)
FieldRegistry.register(FieldType.CHECKBOX, BooleanField)
FieldRegistry.register(FieldType.SELECT, SelectField)
FieldRegistry.register(FieldType.DATE, DateField)
FieldRegistry.register(FieldType.TEXTAREA, TextAreaField)
FieldRegistry.register(FieldType.RICH_TEXT, RichTextField)
FieldRegistry.register(FieldType.MARKDOWN, MarkdownField)
FieldRegistry.register(FieldType.COLOR, ColorField)
FieldRegistry.register(FieldType.TAGS, TagsField)
FieldRegistry.register(FieldType.KEY_VALUE, KeyValueField)
