from __future__ import annotations

"""Form rendering for admin resources."""

from typing import Any

from starlette.responses import HTMLResponse

from lexigram.admin.auth.services.csrf_service import AdminCsrfService
from lexigram.admin.config import AdminConfig
from lexigram.admin.engine.renderer import AdminRenderer
from lexigram.admin.exceptions import AdminValidationError
from lexigram.admin.rbac.service import PermissionService
from lexigram.admin.resources.data_access import get_resource_data_source
from lexigram.admin.resources.wizard_renderer import WizardRendererMixin
from lexigram.admin.state.context import wants_fragment
from lexigram.di.decorators import inject
from lexigram.logging import get_logger
from lexigram.ui import Form, Modal, SlideOver, Zones, el, render_to_string

logger = get_logger(__name__)

_VALID_FORM_DISPLAY_MODES = {"page", "modal", "slider"}


def _form_display_mode(resource: Any) -> str:
    """Resolve a resource's form display mode with a safe fallback."""
    mode = None
    getter = getattr(resource, "get_form_display_mode", None)
    if callable(getter):
        mode = getter()
    else:
        mode = getattr(resource, "form_display_mode", None)
    return mode if mode in _VALID_FORM_DISPLAY_MODES else "slider"


@inject
class FormRenderer(WizardRendererMixin):
    """Handles rendering of create/edit forms for admin resources."""

    def __init__(
        self,
        config: AdminConfig,
        resource_name: str,
        renderer: AdminRenderer,
        permission_service: PermissionService | None = None,
        resources: dict[str, Any] | None = None,
    ):
        self._config = config
        self.resource_name = resource_name
        self._renderer = renderer
        self._permission_service = permission_service
        self._resources = resources or {}
        self._csrf_service = AdminCsrfService(
            secret=config.auth.session_secret.get_secret_value()
        )

    async def render_create(
        self,
        request,
        resource,
        user=None,
        errors: dict[str, list[str]] | None = None,
    ) -> HTMLResponse:
        """Render create form using Modal/SlideOver components based on form_display_mode."""
        label = self.resource_name.replace("_", " ").title()

        # Check if HTMX request (for modal/slider loading)
        is_htmx = wants_fragment(request)

        # Get form display mode from resource configuration. A page form is
        # always rendered as a normal page, even if a stale client sends an
        # HX target; modal and slider are the only overlay modes.
        display_mode = _form_display_mode(resource)
        overlay_mode = is_htmx and display_mode != "page"
        overlay_target = (
            Zones.MODAL.selector
            if display_mode == "modal"
            else Zones.SLIDE_OVER.selector
        )

        # Build form component
        await self._ensure_csrf_token(request)
        form_component = await self._build_form_component(
            resource,
            label,
            mode="create",
            user=user,
            errors=errors,
            in_slide_over=overlay_mode,
            overlay_target=overlay_target,
            htmx_enabled=display_mode != "page",
        )
        form_component._request = request

        if overlay_mode and display_mode == "modal":
            overlay = Modal(
                title=f"Create {label}",
                trigger=None,
                render_trigger=False,
                is_open=True,
                children=[form_component],
            )
            return HTMLResponse(render_to_string(overlay))
        if overlay_mode:
            overlay = SlideOver(
                title=f"Create {label}",
                subtitle=f"Fill in the details to create a new {label.lower()} record.",
                trigger=None,
                render_trigger=False,
                is_open=True,
                size="xl",
                children=[form_component],
            )
            return HTMLResponse(render_to_string(overlay))

        # Full page render
        content = el(
            "div",
            el(
                "div",
                el(
                    "a",
                    f"← Back to {label}",
                    href=f"{self._config.prefix}/{self.resource_name}",
                    class_="text-primary-600 hover:text-primary-900",
                ),
                el(
                    "h1",
                    f"Create {label}",
                    class_="text-2xl font-bold text-foreground mt-2",
                ),
                class_="mb-6",
            ),
            el(
                "div",
                form_component,
                class_="bg-card shadow rounded-lg p-6",
            ),
            class_="resource-content",
        )

        return self._renderer.render_page(
            content,
            request=request,
            title=f"Create {label}",
            breadcrumbs=[
                {"label": "Dashboard", "url": self._config.prefix},
                {"label": label, "url": f"{self._config.prefix}/{self.resource_name}"},
                {
                    "label": "Create",
                    "url": f"{self._config.prefix}/{self.resource_name}/create",
                },
            ],
        )

    async def render_edit(
        self,
        request,
        resource,
        item_id: str,
        user=None,
        errors: dict[str, list[str]] | None = None,
    ) -> HTMLResponse:
        """Render edit form using Modal/SlideOver components based on form_display_mode."""
        label = self.resource_name.replace("_", " ").title()

        # Check if HTMX request (for modal/slide-over loading)
        is_htmx = wants_fragment(request)

        # Get form display mode from resource configuration.
        display_mode = _form_display_mode(resource)
        overlay_mode = is_htmx and display_mode != "page"
        overlay_target = (
            Zones.MODAL.selector
            if display_mode == "modal"
            else Zones.SLIDE_OVER.selector
        )

        # Fetch existing item data for edit
        initial_data = await self._fetch_item_data(resource, item_id)

        # Build form component with initial data
        await self._ensure_csrf_token(request)
        form_component = await self._build_form_component(
            resource,
            label,
            mode="edit",
            initial_data=initial_data,
            record_id=item_id,
            user=user,
            errors=errors,
            in_slide_over=overlay_mode,
            overlay_target=overlay_target,
            htmx_enabled=display_mode != "page",
        )
        form_component._request = request

        if overlay_mode and display_mode == "modal":
            overlay = Modal(
                title=f"Edit {label}",
                trigger=None,
                render_trigger=False,
                is_open=True,
                children=[form_component],
            )
            return HTMLResponse(render_to_string(overlay))
        if overlay_mode:
            overlay = SlideOver(
                title=f"Edit {label}",
                subtitle=f"Editing record #{item_id}",
                trigger=None,
                render_trigger=False,
                is_open=True,
                size="xl",
                children=[form_component],
            )
            return HTMLResponse(render_to_string(overlay))

        # Full page render
        content = el(
            "div",
            el(
                "div",
                el(
                    "a",
                    f"← Back to {label} #{item_id}",
                    href=f"{self._config.prefix}/{self.resource_name}/{item_id}",
                    class_="text-primary-600 hover:text-primary-900",
                ),
                el(
                    "h1",
                    f"Edit {label} #{item_id}",
                    class_="text-2xl font-bold text-foreground mt-2",
                ),
                class_="mb-6",
            ),
            el(
                "div",
                form_component,
                class_="bg-card shadow rounded-lg p-6",
            ),
            class_="resource-content",
        )

        return self._renderer.render_page(
            content,
            request=request,
            title=f"Edit {label} #{item_id}",
            breadcrumbs=[
                {"label": "Dashboard", "url": self._config.prefix},
                {"label": label, "url": f"{self._config.prefix}/{self.resource_name}"},
                {
                    "label": f"#{item_id}",
                    "url": f"{self._config.prefix}/{self.resource_name}/{item_id}",
                },
                {
                    "label": "Edit",
                    "url": f"{self._config.prefix}/{self.resource_name}/{item_id}/edit",
                },
            ],
        )

    async def _fetch_item_data(self, resource, item_id: str) -> dict:
        """Fetch existing item data for edit mode."""
        initial_data: dict[str, Any] = {}
        try:
            if (
                hasattr(resource, "service")
                and resource.service
                and hasattr(resource.service, "get")
            ):
                item = await resource.service.get(item_id)
                if item:
                    initial_data = (
                        item.model_dump() if hasattr(item, "model_dump") else dict(item)
                    )
            else:
                data_source = get_resource_data_source(resource)
                if data_source is None or not hasattr(data_source, "find_one"):
                    return initial_data
                item = await data_source.find_one(item_id)
                if item:
                    initial_data = (
                        item.model_dump() if hasattr(item, "model_dump") else dict(item)
                    )
        except (AttributeError, TypeError, ValueError, RuntimeError) as e:
            logger.debug(
                "Failed to get item %s/%s for edit: %s",
                self.resource_name,
                item_id,
                e,
            )
        return initial_data

    async def _ensure_csrf_token(self, request) -> None:
        if getattr(getattr(request, "state", None), "csrf_token", None):
            return
        # Must mirror AdminCsrfMiddleware._validate_csrf exactly: tokens are
        # bound to csrf_session_id, else admin_user_id, else "anonymous".
        session_id = request.session.get("csrf_session_id") or request.session.get(
            "admin_user_id", "anonymous"
        )
        request.state.csrf_token = self._csrf_service.generate_token(session_id)

    async def _build_form_component(
        self,
        resource,
        label: str,
        mode: str = "create",
        initial_data: dict | None = None,
        record_id: str | None = None,
        user=None,
        errors: dict[str, list[str]] | None = None,
        in_slide_over: bool = False,
        overlay_target: str = Zones.SLIDE_OVER.selector,
        htmx_enabled: bool = True,
    ) -> Any:
        """Build a Form component from resource model or form_class.

        Args:
            resource: The resource class
            label: Human-readable label for the resource
            mode: 'create' or 'edit'
            initial_data: Initial values for edit mode
            record_id: Record ID for edit mode

        Returns:
            Form component ready for rendering
        """
        initial_data = initial_data or {}

        # Determine form action URL
        if mode == "edit" and record_id:
            action_url = f"{self._config.prefix}/{self.resource_name}/{record_id}/edit"
        else:
            action_url = f"{self._config.prefix}/{self.resource_name}/create"

        # Try to use resource's form_class first
        form_class = None
        if resource and hasattr(resource, "get_form_class"):
            form_class = resource.get_form_class()
        elif resource and hasattr(resource, "form_class"):
            form_class = resource.form_class

        if form_class:
            # Use the declared form class. Overlay embeds suppress the in-form
            # action bar — the panel/modal footer owns Cancel/Save and is bound
            # to the form via the ``form`` attribute.
            submit_label = "Update" if mode == "edit" else "Create"
            form = form_class(
                initial=initial_data,
                action=action_url,
                form_id=f"{self.resource_name}-{mode}-form",
                submit_label=submit_label,
                suppress_submit=in_slide_over,
                hx_post=action_url if htmx_enabled else None,
                hx_target=overlay_target if htmx_enabled else None,
                hx_swap="innerHTML",
            )
            await self._populate_form_relation_options(form)
            return form

        # Generate form from Pydantic model
        if resource and resource.model:
            try:
                from dataclasses import replace as dc_replace

                from lexigram.admin.forms.components import FormSchemaGenerator

                generator = FormSchemaGenerator(
                    resource_registry=dict(self._resources)
                )
                schema = generator.from_pydantic(resource.model)

                # Populate relation field options from the related resource's
                # registered instance/class (IDataSource protocol: find_many).
                await self._populate_relation_options(schema)

                # Build field components from schema
                rendered_fields: dict[str, Any] = {}
                ordered_names: list[str] = []
                exclude_names = set(getattr(resource, "form_exclude_fields", ()) or ())
                for field_schema in schema.fields:
                    # Skip framework-managed / excluded / form-hidden fields
                    if field_schema.name in exclude_names:
                        continue
                    if not getattr(field_schema, "visible_in_form", True):
                        continue

                    # --- Field-level RBAC enforcement ---
                    if user:
                        if self._permission_service is not None:
                            _perm_svc = self._permission_service
                            # Hide field if user lacks view permission
                            if not await _perm_svc.can_view_field(
                                user, self.resource_name, field_schema.name
                            ):
                                continue
                            # Mark field non-editable if user lacks edit permission
                            if mode == "edit" and not await _perm_svc.can_edit_field(
                                user, self.resource_name, field_schema.name
                            ):
                                field_schema = dc_replace(field_schema, readonly=True)
                    # --- end RBAC ---

                    field_value = initial_data.get(
                        field_schema.name,
                        field_schema.default,
                    )

                    # Create the appropriate field component based on type
                    field_component = self._create_field_component(
                        field_schema,
                        field_value,
                    )
                    if field_component:
                        if errors and field_schema.name in errors:
                            field_component.error = errors[field_schema.name]
                        rendered_fields[field_schema.name] = field_component.render()
                        ordered_names.append(field_schema.name)

                submit_label = "Update" if mode == "edit" else "Create"

                # Declared form layout (FormSection groups) wins; otherwise
                # fields render flat in schema order.
                layout_sections = self._resolve_form_sections(resource)
                if layout_sections:
                    body_fields = self._render_layout_fields(
                        layout_sections,
                        rendered_fields,
                        ordered_names,
                    )
                else:
                    body_fields = [rendered_fields[n] for n in ordered_names]

                # Create Form component with fields.  HTMX submits swap the
                # validation-error response back into the slide-over zone so
                # the drawer stays open; full-page renders ignore hx-* attrs.
                form = Form(
                    action_url=action_url,
                    method="post",
                    submit_label=submit_label,
                    form_id=f"{self.resource_name}-{mode}-form",
                    suppress_submit=in_slide_over,
                    htmx_enabled=htmx_enabled,
                    hx_target=overlay_target,
                    hx_swap="innerHTML",
                )
                form.children = body_fields
                return form

            except AdminValidationError as e:
                logger.debug(
                    "Failed to generate form for %s: %s",
                    self.resource_name,
                    e,
                )
                return el("p", f"Error generating form: {e}", class_="text-destructive")

        return el(
            "p",
            "No form configuration available for this resource.",
            class_="text-muted-foreground",
        )

    def _resolve_related_resource(self, resource_name: str) -> Any | None:
        """Resolve a registered resource instance/class by resource name.

        Resource instances are resolved at mount time and shared through the
        route registry, so relation options load from the same data source the
        related resource uses at runtime (including search wrappers).
        """
        if not resource_name:
            return None
        entry = self._resources.get(resource_name)
        if entry is None:
            return None
        return entry() if isinstance(entry, type) else entry

    @staticmethod
    def _relation_option(record: Any) -> tuple[str, str] | None:
        """Convert a related record into a stable select option.

        Data sources commonly return dictionaries, while tests and domain
        adapters may return objects. ``getattr(record, "id", record)`` turns a
        dictionary into its entire repr, so normalize both shapes explicitly
        and choose a useful human label without changing the submitted ID.
        """
        if isinstance(record, dict):
            record_id = record.get("id", record.get("pk"))
            label = (
                record.get("name")
                or record.get("title")
                or record.get("label")
                or record.get("email")
                or record_id
            )
        else:
            record_id = getattr(record, "id", getattr(record, "pk", None))
            label = (
                getattr(record, "name", None)
                or getattr(record, "title", None)
                or getattr(record, "label", None)
                or getattr(record, "email", None)
                or record_id
            )
        if record_id is None:
            return None
        return str(record_id), str(label if label is not None else record_id)

    async def _populate_form_relation_options(self, form: Any) -> None:
        """Populate relation options on a declared FormBase instance.

        FormBase keeps an instance-local ``fields`` mapping, so replacing a
        frozen relation field here does not mutate the resource's shared form
        class or leak one request's options into another request.
        """
        fields = getattr(form, "fields", None)
        if not isinstance(fields, dict):
            return
        from dataclasses import replace as dc_replace
        from lexigram.admin.data.query import QuerySpec
        from lexigram.admin.schema import BelongsToField, HasManyField

        for name, field_schema in list(fields.items()):
            if not isinstance(field_schema, (BelongsToField, HasManyField)):
                continue
            related = self._resolve_related_resource(field_schema.resource)
            ds = get_resource_data_source(related)
            if ds is None or not hasattr(ds, "find_many"):
                continue
            try:
                result = await ds.find_many(QuerySpec(per_page=200, sort_by="id"))
                records = (
                    result.items
                    if hasattr(result, "items")
                    else result
                    if isinstance(result, list)
                    else []
                )
                options = [
                    option
                    for record in records
                    if (option := self._relation_option(record)) is not None
                ]
                fields[name] = dc_replace(field_schema, options=options)
            except Exception:
                logger.debug(
                    "Failed to load options for %s.%s",
                    self.resource_name,
                    name,
                )

    async def _populate_relation_options(self, schema: Any) -> None:
        """Load selectable options for relation fields into the form schema.

        Handles belongs-to and has-many relation fields; the related resource
        must be registered and expose an ``IDataSource``-compatible
        ``find_many``. Failures are non-fatal (the field renders empty).
        """
        from dataclasses import replace as dc_replace

        from lexigram.admin.data.query import QuerySpec
        from lexigram.admin.schema import BelongsToField, HasManyField

        for idx, field_schema in enumerate(schema.fields):
            if not isinstance(field_schema, (BelongsToField, HasManyField)):
                continue
            related = self._resolve_related_resource(field_schema.resource)
            if related is None:
                continue
            ds = get_resource_data_source(related)
            if ds is None or not hasattr(ds, "find_many"):
                continue
            try:
                result = await ds.find_many(QuerySpec(per_page=200, sort_by="id"))
                if hasattr(result, "items"):
                    records = result.items
                elif isinstance(result, list):
                    records = result
                else:
                    records = []
                options = [
                    option
                    for record in records
                    if (option := self._relation_option(record)) is not None
                ]
                schema.fields[idx] = dc_replace(field_schema, options=options)
            except Exception:
                logger.debug(
                    "Failed to load options for %s.%s",
                    self.resource_name,
                    field_schema.name,
                )

    @staticmethod
    def _resolve_form_sections(resource: Any) -> list[Any]:
        """Resolve declared form layout sections for a resource."""
        getter = getattr(resource, "get_form_sections", None)
        if callable(getter):
            sections = getter()
            if isinstance(sections, list):
                return sections
        return list(getattr(resource, "form_sections", ()) or ())

    @staticmethod
    def _render_layout_fields(
        sections: list[Any],
        rendered_fields: dict[str, Any],
        ordered_names: list[str],
    ) -> list[Any]:
        """Render fields grouped into declared sections, then leftovers.

        Each declared section becomes one :class:`Section` layout node
        (``lexigram.admin.forms.layout``) whose ``FieldNode`` children resolve
        to the already-rendered field atoms, so the generated form shares the
        exact section visuals and ``visible_when`` semantics of declarative
        ``FormBase`` layouts. Fields not referenced by any section are
        appended after the sections (in schema order) so nothing declared on
        the model is lost.
        """

        from lexigram.admin.forms.layout import FieldNode, Section
        from lexigram.ui import el

        class _RenderedField:
            def __init__(self, element: Any) -> None:
                self._element = element

            def render_form(
                self,
                value: Any = None,
                *,
                errors: list[str] | None = None,
            ) -> Any:
                return self._element

        class _FieldsForm:
            def __init__(self, fields: dict[str, Any]) -> None:
                self.fields = fields

        assigned: set[str] = set()
        body: list[Any] = []
        for section in sections:
            section_names = [
                name
                for name in getattr(section, "fields", ())
                if name in rendered_fields
            ]
            if not section_names:
                continue
            assigned.update(section_names)
            try:
                columns = max(1, min(4, int(getattr(section, "columns", 1) or 1)))
            except (TypeError, ValueError):
                columns = 1
            node = Section(
                title=getattr(section, "title", None),
                description=getattr(section, "description", None),
                columns=columns,
                children=[
                    FieldNode(field_name=name) for name in section_names
                ],
            )
            form = _FieldsForm(
                {name: _RenderedField(rendered_fields[name]) for name in section_names}
            )
            body.append(node.render(form))  # type: ignore[arg-type]

        leftovers = [
            rendered_fields[name] for name in ordered_names if name not in assigned
        ]
        if leftovers:
            body.append(el("div", *leftovers, class_="space-y-6"))
        return body

    def _create_field_component(self, field_schema, value) -> Any:
        """Create a field component from a SchemaField.

        Args:
            field_schema: The schema field definition
            value: Initial value for the field

        Returns:
            Field component instance
        """
        from lexigram.admin.resources.field_renderer import _field_renderer_registry

        common_args = {
            "label": field_schema.label,
            "required": field_schema.required,
            "readonly": field_schema.readonly,
            "help_text": field_schema.help_text,
            "default": field_schema.default,
            "placeholder": field_schema.placeholder,
            "name": field_schema.name,
        }
        # Searchable relation selects load options over HTMX from the related
        # resource's registered relation-options endpoint.
        if getattr(field_schema, "searchable", False) and field_schema.resource:
            common_args["relation_options_url"] = (
                f"{self._config.prefix.rstrip('/')}/{field_schema.resource}"
                "/relation-options"
            )

        # Use registry to get the appropriate renderer and field instance
        renderer = _field_renderer_registry.get_renderer(field_schema)
        return renderer.render_field(field_schema, value, common_args)


__all__ = ["FormRenderer"]
