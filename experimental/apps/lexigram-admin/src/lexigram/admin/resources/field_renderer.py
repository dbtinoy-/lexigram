"""Field rendering for admin resources."""

from __future__ import annotations

from typing import Any

from starlette.responses import HTMLResponse

from lexigram.admin.config import AdminConfig
from lexigram.admin.resources.data_access import get_resource_data_source
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
from lexigram.admin.resources.urls import admin_prefix_from_request
from lexigram.admin.schema import SchemaField
from lexigram.di.decorators import inject
from lexigram.logging import get_logger
from lexigram.primitives.registry import Registry
from lexigram.serialization import dumps_str
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


#: Registered renderer values are either instances (``register("key", obj)``)
#: or renderer classes (the decorator form ``@register("key")``).
FieldRendererValue = FieldRendererProtocol | type[FieldRendererProtocol]


class FieldRendererRegistry(Registry[str, FieldRendererValue]):
    """Registry of field renderers, resolved by ``can_render`` predicate.

    Built-in renderers are declared in :meth:`_default_entries` (first match
    wins, so specialized renderers must be registered before their general
    fallbacks); applications can register additional renderers with
    ``register()``, ``register_factory()``, or the decorator form.
    """

    def __init__(self) -> None:
        """Create an empty registry — use :meth:`with_defaults` for built-ins.

        ``allow_overwrite`` is enabled because field renderers are an
        application extension point: registering a custom renderer under a
        built-in key (e.g. ``"text"``) intentionally replaces the default.
        """
        super().__init__(name="admin.field_renderers", allow_overwrite=True)

    @classmethod
    def _default_entries(cls) -> dict[str, FieldRendererValue]:
        """Declare the complete in-package built-in renderer set."""
        return {
            "text_area": TextAreaFieldRenderer(),
            "list": ListFieldRenderer(),
            "json": JsonFieldRenderer(),
            "multi_select": MultiSelectFieldRenderer(),
            "has_many": HasManyFieldRenderer(),
            "belongs_to": BelongsToFieldRenderer(),
            "morph": MorphFieldRenderer(),
            "select": SelectFieldRenderer(),
            "date": DateFieldRenderer(),
            "datetime": DateTimeFieldRenderer(),
            "email": EmailFieldRenderer(),
            "password": PasswordFieldRenderer(),
            "color": ColorFieldRenderer(),
            "number": NumberFieldRenderer(),
            "boolean": BooleanFieldRenderer(),
            "text": TextFieldRenderer(),
            "default": DefaultFieldRenderer(),
        }

    def get_renderer(self, field_schema: SchemaField) -> FieldRendererProtocol:
        """Return the first registered renderer that can render *field_schema*.

        Both instance registrations (``register("key", MyRenderer())``) and
        class registrations (the decorator form ``@register("key")`` on a
        class) are accepted; classes are instantiated on first resolution.
        Falls back to :class:`DefaultFieldRenderer` when no registered
        renderer matches (or the registry is empty).
        """
        for renderer in self.values():
            if isinstance(renderer, type):
                renderer = renderer()
            if renderer.can_render(field_schema):
                return renderer
        return DefaultFieldRenderer()


# Global registry instance with all built-in renderers.
_field_renderer_registry: FieldRendererRegistry = FieldRendererRegistry.with_defaults()


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

        # Fetch current item data. Prefer the legacy service when explicitly
        # supplied, then fall back to the same shared data-source resolver used
        # by detail/forms/CRUD paths.
        current_data: dict[str, Any] = {}
        if item_id and resource:
            # Use the mounted canonical source even when a deprecated
            # ``service`` attribute remains on the resource.
            data_source = get_resource_data_source(resource)
            try:
                if data_source is not None:
                    getter = getattr(data_source, "get", None) or getattr(
                        data_source, "find_one", None
                    )
                    if getter is not None:
                        item = await getter(item_id)
                        if item:
                            current_data = (
                                item.model_dump()
                                if hasattr(item, "model_dump")
                                else dict(item)
                                if isinstance(item, dict)
                                else dict(vars(item))
                                if hasattr(item, "__dict__")
                                else {}
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
            csrf_token=getattr(getattr(request, "state", None), "csrf_token", None),
            admin_prefix=admin_prefix_from_request(request),
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
        csrf_token: str | None = None,
        admin_prefix: str | None = None,
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
        # Resolve the same schema used by generated forms. Declarative
        # resources may intentionally omit a model and provide SchemaField
        # instances directly.
        if not resource:
            return None

        try:
            field_schema = next(
                (
                    fs
                    for fs in getattr(resource, "fields", ()) or ()
                    if getattr(fs, "name", None) == field_name
                ),
                None,
            )
            if field_schema is None:
                model = getattr(resource, "model", None)
                if model is not None:
                    from lexigram.admin.forms.components import FormSchemaGenerator

                    schema = FormSchemaGenerator().from_pydantic(model)
                    field_schema = next(
                        (fs for fs in schema.fields if fs.name == field_name),
                        None,
                    )
            if field_schema is None:
                return None

            # Skip auto-generated fields
            if field_name in ("id", "created_at", "updated_at"):
                return None

            # Create the appropriate field component based on type
            return self._create_field_component(
                field_schema,
                value,
                item_id,
                csrf_token=csrf_token,
                admin_prefix=admin_prefix,
            )

        except (ImportError, AttributeError, TypeError, ValueError) as e:
            logger.debug(
                "Failed to build field component for %s.%s: %s",
                self.resource_name,
                field_name,
                e,
            )
            return None

    def _create_field_component(
        self,
        field_schema,
        value,
        item_id: str | None = None,
        csrf_token: str | None = None,
        admin_prefix: str | None = None,
    ) -> Any:
        """Create a field component from a FieldSchema for inline editing.

        Args:
            field_schema: The field schema definition
            value: Current value for the field
            item_id: ID of the item being edited

        Returns:
            Field component instance configured for inline editing
        """
        # Determine action URL for inline editing. Resolve the active mount
        # from the request path so an editor loaded under a custom prefix does
        # not submit back to the default ``/admin`` mount.
        prefix = (admin_prefix or self._config.prefix).rstrip("/")
        action_url = (
            f"{prefix}/{self.resource_name}/{item_id}/field/{field_schema.name}"
        )

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
        if csrf_token:
            common_args["hx_headers"] = dumps_str({"X-CSRF-Token": csrf_token})

        # Use registry to get the appropriate renderer
        renderer = _field_renderer_registry.get_renderer(field_schema)
        return renderer.render_field(field_schema, value, common_args)
