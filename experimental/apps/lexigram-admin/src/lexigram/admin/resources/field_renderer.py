from __future__ import annotations

"""Field rendering for admin resources."""

from typing import Any, Protocol

from starlette.responses import HTMLResponse

from lexigram.admin.config import AdminConfig
from lexigram.admin.schema import (
    BelongsToField,
    BooleanField,
    ColorField,
    DateField,
    DateTimeField,
    EmailField,
    HasManyField,
    JsonField,
    MorphField,
    MultiSelectField,
    NumberField,
    PasswordField,
    SchemaField,
    SelectField,
    TagsField,
    TextAreaField,
    TextField,
)
from lexigram.di.decorators import inject
from lexigram.logging import get_logger
from lexigram.serialization import dumps_str
from lexigram.ui import (
    BelongsTo,
    DateInput,
    MultiSelect,
    NumberInput,
    Select,
    Switch,
    TextArea,
    TextInput,
    el,
    render_to_string,
)

logger = get_logger(__name__)


class FieldRendererProtocol(Protocol):
    """Protocol for field renderers."""

    def can_render(self, field_schema: SchemaField) -> bool: ...

    def render_field(
        self,
        field_schema: SchemaField,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any: ...


def _atom_args(
    common_args: dict[str, Any], value: Any, extra: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build atom kwargs from shared inline-editing args.

    Args:
        common_args: Shared args (name, label, required, disabled, hx_*, ...).
        value: Current field value.
        extra: Additional atom-specific kwargs.

    Returns:
        Kwargs acceptable by lexigram.ui input atoms.
    """
    args: dict[str, Any] = {
        "name": common_args["name"],
        "value": value if value is not None else "",
        "label": common_args.get("label"),
        "required": common_args.get("required", False),
        "disabled": common_args.get("disabled", False),
    }
    for key in ("placeholder", "error"):
        if common_args.get(key):
            args[key] = common_args[key]
    args.update({k: v for k, v in common_args.items() if k.startswith("hx_")})
    if extra:
        args.update(extra)
    return args


class TextAreaFieldRenderer:
    """Renderer for multi-line text fields."""

    def can_render(self, field_schema: SchemaField) -> bool:
        return isinstance(field_schema, TextAreaField)

    def render_field(
        self,
        field_schema: SchemaField,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        return TextArea(**_atom_args(common_args, value))


class ListFieldRenderer:
    """Renderer for tag-style list fields (comma-joined text area)."""

    def can_render(self, field_schema: SchemaField) -> bool:
        return isinstance(field_schema, TagsField)

    def render_field(
        self,
        field_schema: SchemaField,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        display_value = (
            ", ".join(str(v) for v in value)
            if isinstance(value, list)
            else str(value or "")
        )
        return TextArea(**_atom_args(common_args, display_value))


class JsonFieldRenderer:
    """Renderer for JSON fields."""

    def can_render(self, field_schema: SchemaField) -> bool:
        return isinstance(field_schema, JsonField)

    def render_field(
        self,
        field_schema: SchemaField,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        display_value = dumps_str(value) if value is not None else ""
        args = _atom_args(common_args, display_value, extra={"rows": 8})
        return TextArea(**args)


class NumberFieldRenderer:
    """Renderer for numeric fields."""

    def can_render(self, field_schema: SchemaField) -> bool:
        return isinstance(field_schema, NumberField)

    def render_field(
        self,
        field_schema: SchemaField,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        return NumberInput(**_atom_args(common_args, value))


class BooleanFieldRenderer:
    """Renderer for boolean fields."""

    def can_render(self, field_schema: SchemaField) -> bool:
        return isinstance(field_schema, BooleanField)

    def render_field(
        self,
        field_schema: SchemaField,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        hx_props = {k: v for k, v in common_args.items() if k.startswith("hx_")}
        return Switch(
            label=common_args.get("label") or "",
            name=common_args["name"],
            value=bool(value),
            **hx_props,
        )


class MultiSelectFieldRenderer:
    """Renderer for multi-select fields."""

    def can_render(self, field_schema: SchemaField) -> bool:
        return isinstance(field_schema, MultiSelectField)

    def render_field(
        self,
        field_schema: SchemaField,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        if not isinstance(field_schema, MultiSelectField):
            return None
        choices = field_schema.options or []
        selected = value if isinstance(value, list) else []
        return MultiSelect(
            **_atom_args(common_args, selected, extra={"choices": choices})
        )


class HasManyFieldRenderer:
    """Renderer for HAS_MANY relation fields."""

    def can_render(self, field_schema: SchemaField) -> bool:
        return isinstance(field_schema, HasManyField)

    def render_field(
        self,
        field_schema: SchemaField,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        if not isinstance(field_schema, HasManyField):
            return None
        choices = field_schema.options or []
        selected = value if isinstance(value, list) else []
        return MultiSelect(
            **_atom_args(common_args, selected, extra={"choices": choices})
        )


class BelongsToFieldRenderer:
    """Renderer for BELONGS_TO relation fields."""

    def can_render(self, field_schema: SchemaField) -> bool:
        return isinstance(field_schema, BelongsToField)

    def render_field(
        self,
        field_schema: SchemaField,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        if not isinstance(field_schema, BelongsToField):
            return None
        return BelongsTo(
            **_atom_args(
                common_args,
                value,
                extra={
                    "resource": field_schema.resource,
                    "choices": field_schema.options or [],
                },
            )
        )


class MorphFieldRenderer:
    """Renderer for polymorphic relation fields."""

    def can_render(self, field_schema: SchemaField) -> bool:
        return isinstance(field_schema, MorphField)

    def render_field(
        self,
        field_schema: SchemaField,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        if not isinstance(field_schema, MorphField):
            return None
        args = _atom_args(
            common_args, value, extra={"choices": field_schema.options or []}
        )
        return Select(**args)


class SelectFieldRenderer:
    """Renderer for select fields."""

    def can_render(self, field_schema: SchemaField) -> bool:
        return isinstance(field_schema, SelectField)

    def render_field(
        self,
        field_schema: SchemaField,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        if not isinstance(field_schema, SelectField):
            return None
        args = _atom_args(
            common_args, value, extra={"choices": field_schema.options or []}
        )
        return Select(**args)


class DateFieldRenderer:
    """Renderer for date fields."""

    def can_render(self, field_schema: SchemaField) -> bool:
        return isinstance(field_schema, DateField)

    def render_field(
        self,
        field_schema: SchemaField,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        iso_value = value.isoformat() if value is not None else ""
        return DateInput(**_atom_args(common_args, iso_value))


class DateTimeFieldRenderer:
    """Renderer for datetime fields."""

    def can_render(self, field_schema: SchemaField) -> bool:
        return isinstance(field_schema, DateTimeField)

    def render_field(
        self,
        field_schema: SchemaField,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        iso_value = value.isoformat() if value is not None else ""
        return DateInput(**_atom_args(common_args, iso_value))


class EmailFieldRenderer:
    """Renderer for email fields."""

    def can_render(self, field_schema: SchemaField) -> bool:
        return isinstance(field_schema, EmailField)

    def render_field(
        self,
        field_schema: SchemaField,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        return TextInput(
            **_atom_args(common_args, value, extra={"input_type": "email"})
        )


class PasswordFieldRenderer:
    """Renderer for password fields."""

    def can_render(self, field_schema: SchemaField) -> bool:
        return isinstance(field_schema, PasswordField)

    def render_field(
        self,
        field_schema: SchemaField,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        return TextInput(
            **_atom_args(common_args, value, extra={"input_type": "password"})
        )


class ColorFieldRenderer:
    """Renderer for color fields."""

    def can_render(self, field_schema: SchemaField) -> bool:
        return isinstance(field_schema, ColorField)

    def render_field(
        self,
        field_schema: SchemaField,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        return TextInput(
            **_atom_args(common_args, value, extra={"input_type": "color"})
        )


class TextFieldRenderer:
    """Renderer for plain text fields."""

    def can_render(self, field_schema: SchemaField) -> bool:
        return isinstance(field_schema, TextField)

    def render_field(
        self,
        field_schema: SchemaField,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        return TextInput(**_atom_args(common_args, value))


class DefaultFieldRenderer:
    """Default renderer for unknown field types."""

    def can_render(self, field_schema: SchemaField) -> bool:
        return True

    def render_field(
        self,
        field_schema: SchemaField,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        return TextInput(**_atom_args(common_args, value))


class FieldRendererRegistry:
    """Registry for field renderers."""

    def __init__(self) -> None:
        self._renderers: list[FieldRendererProtocol] = [
            TextAreaFieldRenderer(),
            ListFieldRenderer(),
            JsonFieldRenderer(),
            MultiSelectFieldRenderer(),
            HasManyFieldRenderer(),
            BelongsToFieldRenderer(),
            MorphFieldRenderer(),
            SelectFieldRenderer(),
            DateFieldRenderer(),
            DateTimeFieldRenderer(),
            EmailFieldRenderer(),
            PasswordFieldRenderer(),
            ColorFieldRenderer(),
            NumberFieldRenderer(),
            BooleanFieldRenderer(),
            TextFieldRenderer(),
            DefaultFieldRenderer(),
        ]

    def get_renderer(self, field_schema: SchemaField) -> FieldRendererProtocol:
        for renderer in self._renderers:
            if renderer.can_render(field_schema):
                return renderer
        return DefaultFieldRenderer()


# Global registry instance
_field_renderer_registry = FieldRendererRegistry()


@inject
class FieldRenderer:
    """Handles rendering of individual field components for admin resources."""

    def __init__(self, config: AdminConfig, resource_name: str):
        self._config = config
        self.resource_name = resource_name

    async def render_field(
        self,
        request,
        resource,
        field_name: str,
        item_id: str | None = None,
        user=None,
    ) -> HTMLResponse:
        """Render a single field for inline editing."""
        self.resource_name.replace("_", " ").title()

        # Fetch current item data
        current_data: dict[str, Any] = {}
        if item_id and resource and hasattr(resource, "service") and resource.service:
            try:
                if hasattr(resource.service, "get"):
                    item = await resource.service.get(item_id)
                    if item:
                        current_data = (
                            item.model_dump()
                            if hasattr(item, "model_dump")
                            else dict(item)
                        )
            except (AttributeError, TypeError, ValueError, RuntimeError) as e:
                logger.debug(
                    "Failed to get item %s/%s for field edit: %s",
                    self.resource_name,
                    item_id,
                    e,
                )

        # Get field value
        field_value = current_data.get(field_name, "")

        # Build field component
        field_component = self._build_field_component(
            resource,
            field_name,
            field_value,
            item_id,
        )

        if not field_component:
            return HTMLResponse(
                el("span", "Field not found", class_="text-destructive"),
                status_code=404,
            )

        # Return just the field component for HTMX inline editing
        return HTMLResponse(render_to_string(field_component))

    def _build_field_component(
        self,
        resource,
        field_name: str,
        value,
        item_id: str | None = None,
    ) -> Any:
        """Build a field component for inline editing.

        Args:
            resource: The resource class
            field_name: Name of the field to render
            value: Current value of the field
            item_id: ID of the item being edited (for inline editing)

        Returns:
            Field component ready for rendering
        """
        # Try to get field schema from resource model
        if not resource or not resource.model:
            return None

        try:
            from lexigram.admin.forms.components import FormSchemaGenerator

            generator = FormSchemaGenerator()
            schema = generator.from_pydantic(resource.model)

            # Find the field schema
            field_schema = None
            for fs in schema.fields:
                if fs.name == field_name:
                    field_schema = fs
                    break

            if not field_schema:
                return None

            # Skip auto-generated fields
            if field_name in ("id", "created_at", "updated_at"):
                return None

            # Create the appropriate field component based on type
            return self._create_field_component(field_schema, value, item_id)

        except (ImportError, AttributeError, TypeError, ValueError) as e:
            logger.debug(
                "Failed to build field component for %s.%s: %s",
                self.resource_name,
                field_name,
                e,
            )
            return None

    def _create_field_component(
        self, field_schema, value, item_id: str | None = None
    ) -> Any:
        """Create a field component from a FieldSchema for inline editing.

        Args:
            field_schema: The field schema definition
            value: Current value for the field
            item_id: ID of the item being edited

        Returns:
            Field component instance configured for inline editing
        """
        # Determine action URL for inline editing
        action_url = f"{self._config.prefix}/{self.resource_name}/{item_id}/field/{field_schema.name}"

        common_args = {
            "label": None,  # No label for inline editing
            "required": field_schema.required,
            "readonly": field_schema.readonly,
            "help_text": None,  # No help text for inline editing
            "default": field_schema.default,
            "placeholder": field_schema.placeholder,
            "name": field_schema.name,
            "hx_post": action_url,
            "hx_target": "closest td",  # Replace the table cell
            "hx_swap": "outerHTML",
            "hx_trigger": "change",  # Submit on change
        }

        # Use registry to get the appropriate renderer
        renderer = _field_renderer_registry.get_renderer(field_schema)
        return renderer.render_field(field_schema, value, common_args)


__all__ = [
    "BelongsToFieldRenderer",
    "BooleanFieldRenderer",
    "ColorFieldRenderer",
    "DateFieldRenderer",
    "DateTimeFieldRenderer",
    "DefaultFieldRenderer",
    "EmailFieldRenderer",
    "FieldRenderer",
    "FieldRendererProtocol",
    "FieldRendererRegistry",
    "HasManyFieldRenderer",
    "JsonFieldRenderer",
    "ListFieldRenderer",
    "MorphFieldRenderer",
    "MultiSelectFieldRenderer",
    "NumberFieldRenderer",
    "PasswordFieldRenderer",
    "SelectFieldRenderer",
    "TextAreaFieldRenderer",
    "TextFieldRenderer",
]
