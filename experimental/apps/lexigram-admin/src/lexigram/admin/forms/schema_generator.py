"""Declarative form schema generation.

``FormSchema`` describes a complete form structure; ``FormSchemaGenerator``
builds one from Pydantic models, ``DomainModel``s, or stdlib dataclasses.
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
    Union,
    get_args,
    get_origin,
)

if TYPE_CHECKING:
    from pydantic.fields import FieldInfo

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

    async def filter_for_user(
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
            if not await permission_service.can_view_field(user, resource_name, f.name):
                continue
            schema_field = f
            if not await permission_service.can_edit_field(user, resource_name, f.name):
                schema_field = dataclasses.replace(f, readonly=True)
            fields.append(schema_field)
        return dataclasses.replace(self, fields=fields)


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
        field = self._build_field(
            name,
            field_info.annotation,
            label=label,
            required=is_required,
            help_text=field_info.description,
            default=default,
        )
        # Field-level visibility: json_schema_extra={"visible_in_form": False}
        # hides a field from generated forms (still present on the model).
        extra = getattr(field_info, "json_schema_extra", None)
        if isinstance(extra, dict) and not extra.get("visible_in_form", True):
            field = dataclasses.replace(field, visible_in_form=False)
        return field

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
