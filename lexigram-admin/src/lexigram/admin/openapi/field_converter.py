from __future__ import annotations

from typing import Any

from lexigram.admin.schema import (
    AvatarField,
    BelongsToField,
    BooleanField,
    ColorField,
    CurrencyField,
    DateField,
    DateTimeField,
    EmailField,
    EnumField,
    FileField,
    FloatField,
    HasManyField,
    HiddenField,
    ImageField,
    IntegerField,
    JsonField,
    KeyValueField,
    MarkdownField,
    MorphField,
    MultiSelectField,
    NumberField,
    PasswordField,
    RadioField,
    RatingField,
    RelationField,
    RichTextField,
    SelectField,
    TagsField,
    TextAreaField,
    TextField,
    TimeField,
    ToggleField,
    URLField,
)
from lexigram.admin.schema.base import SchemaField
from lexigram.admin.schema.validators import (
    LengthValidator,
    PatternValidator,
    RangeValidator,
    RequiredValidator,
)

_CONVERTERS: dict[type[SchemaField], Any] = {}


def _register(cls: type[SchemaField]) -> Any:
    """Decorator to register a converter for a SchemaField subclass."""

    def decorator(fn: Any) -> Any:
        _CONVERTERS[cls] = fn
        return fn

    return decorator


# -- String types --


@_register(TextField)
@_register(TextAreaField)
@_register(MarkdownField)
@_register(RichTextField)
@_register(ColorField)
@_register(HiddenField)
def _string(_field: SchemaField) -> dict[str, Any]:
    return {"type": "string"}


@_register(EmailField)
def _email(_field: SchemaField) -> dict[str, Any]:
    return {"type": "string", "format": "email"}


@_register(PasswordField)
def _password(_field: SchemaField) -> dict[str, Any]:
    return {"type": "string", "format": "password"}


@_register(URLField)
def _url(_field: SchemaField) -> dict[str, Any]:
    return {"type": "string", "format": "uri"}


# -- Numeric types --


@_register(IntegerField)
def _integer(_field: SchemaField) -> dict[str, Any]:
    return {"type": "integer", "format": "int32"}


@_register(FloatField)
def _float(_field: SchemaField) -> dict[str, Any]:
    return {"type": "number", "format": "float"}


@_register(CurrencyField)
@_register(NumberField)
def _number(_field: SchemaField) -> dict[str, Any]:
    return {"type": "number"}


@_register(RatingField)
def _rating(_field: SchemaField) -> dict[str, Any]:
    return {"type": "integer", "minimum": 1, "maximum": 5}


# -- Boolean types --


@_register(BooleanField)
@_register(ToggleField)
def _boolean(_field: SchemaField) -> dict[str, Any]:
    return {"type": "boolean"}


# -- Date/time types --


@_register(DateField)
def _date(_field: SchemaField) -> dict[str, Any]:
    return {"type": "string", "format": "date"}


@_register(DateTimeField)
def _datetime(_field: SchemaField) -> dict[str, Any]:
    return {"type": "string", "format": "date-time"}


@_register(TimeField)
def _time(_field: SchemaField) -> dict[str, Any]:
    return {"type": "string", "format": "time"}


# -- Selection types --


@_register(SelectField)
@_register(RadioField)
def _select(field: SchemaField) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "string"}
    _add_enum_if_options(field, schema)
    return schema


@_register(EnumField)
def _enum(field: SchemaField) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "string"}
    _add_enum_if_options(field, schema)
    return schema


@_register(MultiSelectField)
@_register(HasManyField)
def _multi_select(field: SchemaField) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "array", "items": {"type": "string"}}
    if hasattr(field, "options") and field.options:
        schema["items"]["enum"] = [opt[0] for opt in field.options]
    return schema


@_register(TagsField)
def _tags(_field: SchemaField) -> dict[str, Any]:
    return {"type": "array", "items": {"type": "string"}}


# -- Relation types --


@_register(RelationField)
@_register(BelongsToField)
@_register(MorphField)
def _relation(_field: SchemaField) -> dict[str, Any]:
    return {"type": "string"}


# -- Complex types --


@_register(JsonField)
def _json(_field: SchemaField) -> dict[str, Any]:
    return {"type": "object"}


@_register(KeyValueField)
def _key_value(_field: SchemaField) -> dict[str, Any]:
    return {"type": "object", "additionalProperties": {"type": "string"}}


# -- File types --


@_register(FileField)
@_register(ImageField)
@_register(AvatarField)
def _file(_field: SchemaField) -> dict[str, Any]:
    return {"type": "string", "format": "binary"}


# -- Helpers --


def _add_enum_if_options(field: SchemaField, schema: dict[str, Any]) -> None:
    """Add enum values to the schema if the field has options."""
    if hasattr(field, "options") and field.options:
        schema["enum"] = [opt[0] for opt in field.options]


def _extract_validator_constraints(
    field: SchemaField,
) -> dict[str, Any]:
    """Extract OpenAPI constraints from field validators."""
    constraints: dict[str, Any] = {}
    for validator in field.validators:
        if isinstance(validator, RequiredValidator):
            pass
        elif isinstance(validator, LengthValidator):
            if validator.min_length is not None:
                constraints["minLength"] = validator.min_length
            if validator.max_length is not None:
                constraints["maxLength"] = validator.max_length
        elif isinstance(validator, RangeValidator):
            if validator.min_value is not None:
                constraints["minimum"] = validator.min_value
            if validator.max_value is not None:
                constraints["maximum"] = validator.max_value
        elif isinstance(validator, PatternValidator):
            constraints["pattern"] = validator._regex.pattern
    return constraints


def field_to_openapi_property(field: SchemaField) -> dict[str, Any]:
    """Convert a SchemaField to an OpenAPI property schema.

    Args:
        field: A SchemaField instance.

    Returns:
        An OpenAPI Schema Object dict representing the field's property
        specification.
    """
    converter = _CONVERTERS.get(type(field))
    if converter is None:
        schema: dict[str, Any] = {"type": "string"}
    else:
        schema = converter(field)

    if not field.nullable:
        schema["nullable"] = False

    if field.readonly:
        schema["readOnly"] = True

    if field.default is not None:
        schema["default"] = field.default

    if field.help_text:
        schema["description"] = field.help_text

    constraints = _extract_validator_constraints(field)
    schema.update(constraints)

    return schema


__all__ = ["field_to_openapi_property"]
