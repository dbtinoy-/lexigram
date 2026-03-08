from __future__ import annotations

"""Field rendering for admin resources."""

from typing import Any, Protocol

from starlette.responses import HTMLResponse

from lexigram.admin.config import AdminConfig
from lexigram.di.decorators import inject
from lexigram.logging import get_logger
from lexigram.ui import el, render_to_string

logger = get_logger(__name__)


class FieldRendererProtocol(Protocol):
    """Protocol for field renderers."""

    def can_render(self, field_type: Any, field_schema: Any) -> bool: ...

    def render_field(
        self,
        field_schema: Any,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any: ...


class TextAreaFieldRenderer:
    """Renderer for TEXTAREA fields."""

    def can_render(self, field_type: Any, field_schema: Any) -> bool:
        from lexigram.admin.forms.fields import FieldType

        return field_type == FieldType.TEXTAREA

    def render_field(
        self,
        field_schema: Any,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        from lexigram.admin.forms.fields import TextAreaField

        return TextAreaField(**common_args)


class NumberFieldRenderer:
    """Renderer for NUMBER fields."""

    def can_render(self, field_type: Any, field_schema: Any) -> bool:
        from lexigram.admin.forms.fields import FieldType

        return field_type == FieldType.NUMBER

    def render_field(
        self,
        field_schema: Any,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        from lexigram.admin.forms.fields import IntegerField

        return IntegerField(**common_args)


class CheckboxFieldRenderer:
    """Renderer for CHECKBOX fields."""

    def can_render(self, field_type: Any, field_schema: Any) -> bool:
        from lexigram.admin.forms.fields import FieldType

        return field_type == FieldType.CHECKBOX

    def render_field(
        self,
        field_schema: Any,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        from lexigram.admin.forms.fields import BooleanField

        return BooleanField(**common_args)


class SelectFieldRenderer:
    """Renderer for SELECT fields."""

    def can_render(self, field_type: Any, field_schema: Any) -> bool:
        from lexigram.admin.forms.fields import FieldType

        return field_type == FieldType.SELECT and field_schema.options

    def render_field(
        self,
        field_schema: Any,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        from lexigram.admin.forms.fields import SelectField

        options = [
            (
                opt.get("value", opt.get("id", "")),
                opt.get("label", opt.get("name", "")),
            )
            for opt in field_schema.options
        ]
        return SelectField(options=options, **common_args)


class DateFieldRenderer:
    """Renderer for DATE/DATETIME fields."""

    def can_render(self, field_type: Any, field_schema: Any) -> bool:
        from lexigram.admin.forms.fields import FieldType

        return field_type in (FieldType.DATE, FieldType.DATETIME)

    def render_field(
        self,
        field_schema: Any,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        from lexigram.admin.forms.fields import DateField

        return DateField(**common_args)


class EmailFieldRenderer:
    """Renderer for EMAIL fields."""

    def can_render(self, field_type: Any, field_schema: Any) -> bool:
        from lexigram.admin.forms.fields import FieldType

        return field_type == FieldType.EMAIL

    def render_field(
        self,
        field_schema: Any,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        from lexigram.admin.forms.fields import TextField

        return TextField(type="email", **common_args)


class PasswordFieldRenderer:
    """Renderer for PASSWORD fields."""

    def can_render(self, field_type: Any, field_schema: Any) -> bool:
        from lexigram.admin.forms.fields import FieldType

        return field_type == FieldType.PASSWORD

    def render_field(
        self,
        field_schema: Any,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        from lexigram.admin.forms.fields import TextField

        return TextField(type="password", **common_args)


class ListFieldRenderer:
    """Renderer for LIST fields (e.g., list[str])."""

    def can_render(self, field_type: Any, field_schema: Any) -> bool:
        from lexigram.admin.forms.fields import FieldType

        return field_type == FieldType.LIST

    def render_field(
        self,
        field_schema: Any,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        from lexigram.admin.forms.fields import TextAreaField

        display_value = (
            ", ".join(str(v) for v in value)
            if isinstance(value, list)
            else str(value or "")
        )
        args = {k: v for k, v in common_args.items() if k != "placeholder"}
        return TextAreaField(
            **args,
            placeholder=common_args.get("placeholder")
            or "Enter comma-separated values",
        )


class BelongsToFieldRenderer:
    """Renders a BELONGS_TO field as a SelectField with related record options."""

    def can_render(self, field_type: Any, field_schema: Any) -> bool:
        from lexigram.admin.forms.fields import FieldType

        return field_type == FieldType.BELONGS_TO

    def render_field(
        self,
        field_schema: Any,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        from lexigram.admin.forms.fields import SelectField

        options = field_schema.options or []
        return SelectField(
            options=[(o.get("value"), o.get("label")) for o in options],
            **common_args,
        )


class HasManyFieldRenderer:
    """Renders a HAS_MANY field as a MultiSelectField."""

    def can_render(self, field_type: Any, field_schema: Any) -> bool:
        from lexigram.admin.forms.fields import FieldType

        return field_type == FieldType.HAS_MANY

    def render_field(
        self,
        field_schema: Any,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        from lexigram.admin.forms.fields import SelectField

        options = field_schema.options or []
        return SelectField(
            options=[(o.get("value"), o.get("label")) for o in options],
            multiple=True,
            **common_args,
        )


class DefaultFieldRenderer:
    """Default renderer for unknown field types."""

    def can_render(self, field_type: Any, field_schema: Any) -> bool:
        return True

    def render_field(
        self,
        field_schema: Any,
        value: Any,
        common_args: dict[str, Any],
    ) -> Any:
        from lexigram.admin.forms.fields import TextField

        return TextField(**common_args)


class FieldRendererRegistry:
    """Registry for field renderers."""

    def __init__(self) -> None:
        self._renderers: list[FieldRendererProtocol] = []
        self._register_renderers()

    def _register_renderers(self) -> None:
        self._renderers = [
            TextAreaFieldRenderer(),
            NumberFieldRenderer(),
            CheckboxFieldRenderer(),
            SelectFieldRenderer(),
            DateFieldRenderer(),
            EmailFieldRenderer(),
            PasswordFieldRenderer(),
            ListFieldRenderer(),
            BelongsToFieldRenderer(),
            HasManyFieldRenderer(),
            DefaultFieldRenderer(),
        ]

    def get_renderer(
        self,
        field_type: Any,
        field_schema: Any,
    ) -> FieldRendererProtocol:
        for renderer in self._renderers:
            if renderer.can_render(field_type, field_schema):
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
                el("span", "Field not found", class_="text-red-500"),
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
            "disabled": not field_schema.editable,
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
        renderer = _field_renderer_registry.get_renderer(
            field_schema.type,
            field_schema,
        )
        field = renderer.render_field(field_schema, value, common_args)

        # Bind the value to the field
        return field.bind(value)


__all__ = [
    "BelongsToFieldRenderer",
    "CheckboxFieldRenderer",
    "DateFieldRenderer",
    "DefaultFieldRenderer",
    "EmailFieldRenderer",
    "FieldRenderer",
    "FieldRendererProtocol",
    "FieldRendererRegistry",
    "HasManyFieldRenderer",
    "NumberFieldRenderer",
    "PasswordFieldRenderer",
    "SelectFieldRenderer",
    # Renderer classes
    "TextAreaFieldRenderer",
]
