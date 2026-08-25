"""Field rendering for admin resources."""

from __future__ import annotations

from typing import Any

from starlette.responses import HTMLResponse

from lexigram.admin.config import AdminConfig
from lexigram.admin.resources.field_renderers_common import (
    FieldRendererProtocol as FieldRendererProtocol,
)
from lexigram.admin.resources.field_renderers_datetime import (
    DateFieldRenderer as DateFieldRenderer,
)
from lexigram.admin.resources.field_renderers_datetime import (
    DateTimeFieldRenderer as DateTimeFieldRenderer,
)
from lexigram.admin.resources.field_renderers_number import (
    BooleanFieldRenderer as BooleanFieldRenderer,
)
from lexigram.admin.resources.field_renderers_number import (
    NumberFieldRenderer as NumberFieldRenderer,
)
from lexigram.admin.resources.field_renderers_relations import (
    BelongsToFieldRenderer as BelongsToFieldRenderer,
)
from lexigram.admin.resources.field_renderers_relations import (
    HasManyFieldRenderer as HasManyFieldRenderer,
)
from lexigram.admin.resources.field_renderers_relations import (
    MorphFieldRenderer as MorphFieldRenderer,
)
from lexigram.admin.resources.field_renderers_select import (
    MultiSelectFieldRenderer as MultiSelectFieldRenderer,
)
from lexigram.admin.resources.field_renderers_select import (
    SelectFieldRenderer as SelectFieldRenderer,
)
from lexigram.admin.resources.field_renderers_text import (
    ColorFieldRenderer as ColorFieldRenderer,
)
from lexigram.admin.resources.field_renderers_text import (
    DefaultFieldRenderer as DefaultFieldRenderer,
)
from lexigram.admin.resources.field_renderers_text import (
    EmailFieldRenderer as EmailFieldRenderer,
)
from lexigram.admin.resources.field_renderers_text import (
    JsonFieldRenderer as JsonFieldRenderer,
)
from lexigram.admin.resources.field_renderers_text import (
    ListFieldRenderer as ListFieldRenderer,
)
from lexigram.admin.resources.field_renderers_text import (
    PasswordFieldRenderer as PasswordFieldRenderer,
)
from lexigram.admin.resources.field_renderers_text import (
    TextAreaFieldRenderer as TextAreaFieldRenderer,
)
from lexigram.admin.resources.field_renderers_text import (
    TextFieldRenderer as TextFieldRenderer,
)
from lexigram.admin.schema import SchemaField
from lexigram.di.decorators import inject
from lexigram.logging import get_logger
from lexigram.ui import el, render_to_string

logger = get_logger(__name__)

__all__ = [
    "BelongsToFieldRenderer",
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
