"""Unified Form Components.
Includes FormBase, FormBuilder, and FormSchemaGenerator.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
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
from lexigram.admin.schema import (
    BelongsToField,
    BooleanField,
    DateField,
    DateTimeField,
    EnumField,
    FloatField,
    HasManyField,
    IntegerField,
    JsonField,
    MorphField,
    MultiSelectField,
    SchemaField,
    TextField,
)
from lexigram.contracts.exceptions import FieldError
from lexigram.result import Err, Ok, Result
from lexigram.ui import Component, el


@dataclass
class FormSchema:
    """Definition of a complete form structure."""

    fields: list[SchemaField] = field(default_factory=list)
    title: str | None = None
    description: str | None = None
    resource_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    layout: Any | None = None

    def get_field(self, name: str) -> SchemaField | None:
        for f in self.fields:
            if f.name == name:
                return f
        return None

    def filter_for_user(
        self,
        user: Any,
        resource_name: str,
        permission_service: Any | None = None,
    ) -> FormSchema:
        """Return a copy of this schema with RBAC rules applied.

        Args:
            user: Current user for permission checks.
            resource_name: Resource the form is rendered for.
            permission_service: PermissionService used for field-level
                checks. When None, the schema is returned unchanged.

        Returns:
            New FormSchema with non-viewable fields removed and
            non-editable fields marked readonly.
        """
        if permission_service is None:
            return self
        fields: list[SchemaField] = []
        for f in self.fields:
            if not permission_service.can_view_field(user, resource_name, f.name):
                continue
            schema_field = f
            if not permission_service.can_edit_field(user, resource_name, f.name):
                schema_field = dataclasses.replace(f, readonly=True)
            fields.append(schema_field)
        return dataclasses.replace(self, fields=fields)


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

    def _parse_pydantic_field(self, name: str, field_info: FieldInfo) -> SchemaField:
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
        default = (
            field_info.default if field_info.default is not PydanticUndefined else None
        )
        return self._build_field(
            name,
            field_info.annotation,
            label=label,
            required=is_required,
            help_text=field_info.description,
            default=default,
        )

    def _parse_dataclass_field(
        self,
        name: str,
        annotation: Any,
        dc_field: Any,
        meta: dict,
    ) -> SchemaField:
        """Parse a stdlib dataclass field into a ``SchemaField``."""
        import dataclasses

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
        return self._build_field(
            name,
            annotation,
            label=meta.get("title") or name.replace("_", " ").title(),
            required=is_required,
            help_text=meta.get("description"),
            default=default,
        )

    def _build_field(
        self,
        name: str,
        annotation: Any,
        *,
        label: str | None = None,
        required: bool = False,
        help_text: str | None = None,
        default: Any = None,
    ) -> SchemaField:
        """Map a model annotation to a ``SchemaField`` instance."""

        def is_model(t: Any) -> bool:
            return isinstance(t, type) and (
                hasattr(t, "model_fields") or hasattr(t, "__dataclass_fields__")
            )

        # Detect belongs-to FK: field ends with _id
        if name.endswith("_id"):
            return BelongsToField(
                name=name,
                label=label,
                help_text=help_text,
                required=required,
                default=default,
                resource=f"{name[:-3]}s",
            )

        origin = get_origin(annotation)
        args = get_args(annotation)

        # Detect polymorphic: Optional[Union[TypeA, TypeB]]
        _union_types = (Union, _builtin_types.UnionType)
        if origin in _union_types:
            inner_types = [t for t in args if t is not type(None)]
            non_primitive = [t for t in inner_types if is_model(t)]
            if len(non_primitive) >= 2:
                return MorphField(
                    name=name,
                    label=label,
                    help_text=help_text,
                    required=required,
                    default=default,
                    resource=name,
                )
            if len(inner_types) == 1:
                return self._build_field(
                    name,
                    inner_types[0],
                    label=label,
                    required=required,
                    help_text=help_text,
                    default=default,
                )
            return TextField(
                name=name,
                label=label,
                help_text=help_text,
                required=required,
                default=default,
            )

        # Detect has-many: list of domain models
        if origin is list and args:
            if is_model(args[0]):
                return HasManyField(
                    name=name,
                    label=label,
                    help_text=help_text,
                    required=required,
                    default=default,
                    resource=f"{args[0].__name__.lower()}s",
                )
            if args[0] is str:
                return MultiSelectField(
                    name=name,
                    label=label,
                    help_text=help_text,
                    required=required,
                    default=default,
                )
            return JsonField(
                name=name,
                label=label,
                help_text=help_text,
                required=required,
                default=default,
            )

        if isinstance(annotation, type) and issubclass(annotation, Enum):
            return EnumField(
                name=name,
                label=label,
                help_text=help_text,
                required=required,
                default=default,
                enum_cls=annotation,
            )
        if annotation is str:
            return TextField(
                name=name,
                label=label,
                help_text=help_text,
                required=required,
                default=default,
            )
        if annotation is int:
            return IntegerField(
                name=name,
                label=label,
                help_text=help_text,
                required=required,
                default=default,
            )
        if annotation is float:
            return FloatField(
                name=name,
                label=label,
                help_text=help_text,
                required=required,
                default=default,
            )
        if annotation is bool:
            return BooleanField(
                name=name,
                label=label,
                help_text=help_text,
                required=required,
                default=default,
            )
        if annotation is date:
            return DateField(
                name=name,
                label=label,
                help_text=help_text,
                required=required,
                default=default,
            )
        if annotation is datetime:
            return DateTimeField(
                name=name,
                label=label,
                help_text=help_text,
                required=required,
                default=default,
            )
        # Nested model → structured JSON input
        if is_model(annotation):
            return JsonField(
                name=name,
                label=label,
                help_text=help_text,
                required=required,
                default=default,
            )
        return TextField(
            name=name,
            label=label,
            help_text=help_text,
            required=required,
            default=default,
        )


def build_form(**fields) -> Form[Any]:
    """Build a simple form dynamically from keyword field configs."""
    from lexigram.admin.forms.builder import FormBuilder

    builder = FormBuilder.create()
    for name, config in fields.items():
        builder.text(name, label=config.get("label"))
    return builder.build()
