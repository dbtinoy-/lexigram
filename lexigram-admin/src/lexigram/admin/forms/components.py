"""Unified Form Components.
Includes FormBase, FormBuilder, and FormSchemaGenerator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import types as _builtin_types
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Union,
    get_args,
    get_origin,
)

if TYPE_CHECKING:
    from pydantic.fields import FieldInfo

    from lexigram.admin.forms.builder import Form

from lexigram.admin.exceptions import AdminValidationError
from lexigram.admin.forms.fields import AbstractField, FieldSchema, FieldType
from lexigram.contracts.exceptions import FieldError
from lexigram.result import Err, Ok, Result
from lexigram.ui import Component, el

try:
    from lexigram.domain import DomainModel

    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False


@dataclass
class FormSchema:
    """Definition of a complete form structure."""

    fields: list[FieldSchema] = field(default_factory=list)
    title: str | None = None
    description: str | None = None
    resource_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    layout: Any | None = None

    def get_field(self, name: str) -> FieldSchema | None:
        for f in self.fields:
            if f.name == name:
                return f
        return None


class FormMeta(type):
    """Metaclass to collect Field instances from class attributes."""

    def __new__(mcs, name, bases, namespace) -> Any:
        fields = {}
        for base in bases:
            if hasattr(base, "_declared_fields"):
                fields.update(base._declared_fields)
        for key, value in list(namespace.items()):
            if isinstance(value, AbstractField):
                fields[key] = value
                value.name = key
        namespace["_declared_fields"] = fields
        return super().__new__(mcs, name, bases, namespace)


class FormBase(Component, metaclass=FormMeta):
    """Base form class with lifecycle and rendering support."""

    _declared_fields: ClassVar[dict[str, AbstractField]]

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
        self.fields: dict[str, AbstractField] = {}
        self.errors: dict[str, list[str]] = {}
        self._initialize_fields()
        if self.data:
            self.is_valid()

    def _initialize_fields(self) -> Any:
        for name, field_proto in self._declared_fields.items():
            value = self.data.get(name)
            if value is None and not self.data:
                value = self.initial.get(name, field_proto.default)
            elif value is None and self.data:
                value = field_proto.default
            self.fields[name] = field_proto.bind(value)

    def is_valid(self) -> bool:
        self.errors = {}
        is_valid = True
        for name, form_field in self.fields.items():
            try:
                form_field.validate(form_field.value)
            except ValueError as e:
                form_field.errors.append(str(e))
                self.errors[name] = [str(e)]
                is_valid = False
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
        return {name: form_field.value for name, form_field in self.fields.items()}

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
            form_content = [field.render() for field in self.fields.values()]
            form_body = el("div", *form_content, class_="space-y-4")

        actions = el(
            "div",
            Button("Submit", type="submit", color="primary"),
            class_="flex justify-end pt-4 border-t border-gray-100 dark:border-gray-700 mt-6",
        )

        attrs = {
            "method": self.method,
            "class": "bg-white p-6 rounded-lg shadow dark:bg-gray-800",
        }
        if self.action:
            attrs["action"] = self.action
        if self.hx_post:
            attrs["hx-post"] = self.hx_post
        if self.hx_target:
            attrs["hx-target"] = self.hx_target

        return el("form", form_body, actions, **attrs)


class FormSchemaGenerator:
    """Generates FormSchema from various data model types."""

    def __init__(self, resource_registry: dict[str, type] | None = None) -> None:
        self.resource_registry = resource_registry

    def from_pydantic(self, model: type) -> FormSchema:
        """Generate a FormSchema from a model class.

        Supports both Pydantic v2 ``BaseModel`` subclasses (via
        ``model_fields``) and ``DomainModel`` / stdlib dataclasses (via
        ``__dataclass_fields__``).
        """
        fields = []
        title = getattr(model, "__name__", "Form")

        # Pydantic v2 BaseModel
        if hasattr(model, "model_fields") and isinstance(model.model_fields, dict):
            for name, field_info in model.model_fields.items():
                fields.append(self._parse_pydantic_field(name, field_info))
        elif hasattr(model, "__dataclass_fields__"):
            # DomainModel / stdlib dataclass
            import dataclasses
            import typing

            type_hints = typing.get_type_hints(model)
            for dc_field in dataclasses.fields(model):
                name = dc_field.name
                annotation = type_hints.get(name)
                meta: dict = dict(dc_field.metadata) if dc_field.metadata else {}
                fields.append(
                    self._parse_dataclass_field(name, annotation, dc_field, meta)
                )
        else:
            raise TypeError(
                f"Unsupported model type: {model!r}. "
                "Expected a Pydantic BaseModel or dataclass-backed DomainModel."
            )

        return FormSchema(fields=fields, title=title)

    def _parse_pydantic_field(self, name: str, field_info: FieldInfo) -> FieldSchema:
        annotation = field_info.annotation
        field_type = self._map_type(name, annotation)
        from pydantic_core import PydanticUndefined

        label = (
            str(field_info.title)
            if field_info.title
            else name.replace("_", " ").title()
        )
        is_required = (
            field_info.is_required() if hasattr(field_info, "is_required") else True
        )
        if (
            field_info.default is not PydanticUndefined
            or field_info.default_factory is not None
        ):
            is_required = False
        nested_schema = None
        if field_type == FieldType.NESTED:
            # Handle Optional[Model], Union[Model, None], or X | None (3.10+)
            origin = get_origin(annotation)
            args = get_args(annotation)
            model_class = annotation
            _union_types = (Union, _builtin_types.UnionType)
            if origin in _union_types:
                for arg in args:
                    if (
                        arg is not type(None)
                        and isinstance(arg, type)
                        and issubclass(arg, DomainModel)
                    ):
                        model_class = arg
                        break

            if isinstance(model_class, type) and issubclass(model_class, DomainModel):
                nested_schema = self.from_pydantic(model_class)

        related_resource = None
        related_field = None
        if field_type == FieldType.BELONGS_TO and name.endswith("_id"):
            related_resource = name[:-3] + "s"
        elif field_type == FieldType.HAS_MANY:
            related_field = None

        return FieldSchema(
            name=name,
            label=label,
            type=field_type,
            required=is_required,
            default=field_info.default
            if field_info.default is not PydanticUndefined
            else None,
            help_text=field_info.description,
            nested_schema=nested_schema,
            related_resource=related_resource,
            related_field=related_field,
        )

    def _parse_dataclass_field(
        self,
        name: str,
        annotation: Any,
        dc_field: Any,
        meta: dict,
    ) -> FieldSchema:
        """Parse a stdlib dataclass field into a ``FieldSchema``."""
        import dataclasses

        field_type = self._map_type(name, annotation)
        label = meta.get("title") or name.replace("_", " ").title()
        description = meta.get("description")
        is_required = (
            dc_field.default is dataclasses.MISSING
            and dc_field.default_factory is dataclasses.MISSING
        )
        default = (
            None
            if is_required
            else (
                dc_field.default
                if dc_field.default is not dataclasses.MISSING
                else None
            )
        )

        nested_schema = None
        if field_type == FieldType.NESTED:
            origin = get_origin(annotation)
            args = get_args(annotation)
            model_class = annotation
            _union_types = (Union, _builtin_types.UnionType)
            if origin in _union_types:
                for arg in args:
                    if (
                        arg is not type(None)
                        and isinstance(arg, type)
                        and hasattr(arg, "__dataclass_fields__")
                    ):
                        model_class = arg
                        break
            if isinstance(model_class, type) and hasattr(
                model_class, "__dataclass_fields__"
            ):
                nested_schema = self.from_pydantic(model_class)

        related_resource = None
        related_field = None
        if field_type == FieldType.BELONGS_TO and name.endswith("_id"):
            related_resource = name[:-3] + "s"
        elif field_type == FieldType.HAS_MANY:
            related_field = None

        return FieldSchema(
            name=name,
            label=label,
            type=field_type,
            required=is_required,
            default=default,
            help_text=description,
            nested_schema=nested_schema,
            related_resource=related_resource,
            related_field=related_field,
        )

    def _map_type(self, field_name: str, annotation: Any) -> FieldType:
        # Detect belongs-to FK: field ends with _id
        if field_name.endswith("_id"):
            return FieldType.BELONGS_TO

        origin = get_origin(annotation)
        args = get_args(annotation)

        # Detect has-many: list of domain models
        if origin is list and args:
            inner = args[0]
            if isinstance(inner, type) and (
                hasattr(inner, "model_fields") or hasattr(inner, "__dataclass_fields__")
            ):
                return FieldType.HAS_MANY

        # Detect polymorphic: Optional[Union[TypeA, TypeB]]
        _union_types = (Union, _builtin_types.UnionType)
        if origin in _union_types:
            inner_types = [t for t in args if t is not type(None)]
            non_primitive = [
                t
                for t in inner_types
                if isinstance(t, type) and hasattr(t, "__dataclass_fields__")
            ]
            if len(non_primitive) >= 2:
                return FieldType.MORPH

        # Original mapping logic follows (unchanged)
        if origin in _union_types:
            for arg in args:
                if arg is not type(None):
                    return self._map_type(field_name, arg)
            return FieldType.TEXT
        if annotation is str:
            return FieldType.TEXT
        if annotation is int or annotation is float:
            return FieldType.NUMBER
        if annotation is bool:
            return FieldType.CHECKBOX
        from datetime import date, datetime

        if annotation is date:
            return FieldType.DATE
        if annotation is datetime:
            return FieldType.DATETIME
        if isinstance(annotation, type) and (
            issubclass(annotation, DomainModel)
            or hasattr(annotation, "__dataclass_fields__")
        ):
            return FieldType.NESTED
        if origin is list:
            return FieldType.LIST
        return FieldType.TEXT


def build_form(**fields) -> Form[Any]:
    """Build a simple form dynamically from keyword field configs."""
    from lexigram.admin.forms.builder import FormBuilder

    builder = FormBuilder.create()
    for name, config in fields.items():
        builder.text(name, label=config.get("label"))
    return builder.build()
