from __future__ import annotations

"""Form rendering for admin resources."""

from typing import Any

from starlette.responses import HTMLResponse

from lexigram.admin.auth.services.csrf_service import AdminCsrfService
from lexigram.admin.config import AdminConfig
from lexigram.admin.engine.renderer import AdminRenderer
from lexigram.admin.exceptions import AdminValidationError
from lexigram.admin.rbac.service import PermissionService
from lexigram.di.decorators import inject
from lexigram.logging import get_logger
from lexigram.ui import Form, SlideOver, el, render_to_string

logger = get_logger(__name__)


@inject
class FormRenderer:
    """Handles rendering of create/edit forms for admin resources."""

    def __init__(
        self,
        config: AdminConfig,
        resource_name: str,
        renderer: AdminRenderer,
        permission_service: PermissionService | None = None,
    ):
        self._config = config
        self.resource_name = resource_name
        self._renderer = renderer
        self._permission_service = permission_service
        self._csrf_service = AdminCsrfService(secret=config.auth.session_secret)

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
        is_htmx = request.headers.get("HX-Request") == "true"

        # Get form display mode from resource configuration
        display_mode = "modal"  # default
        if resource and hasattr(resource, "get_form_display_mode"):
            display_mode = resource.get_form_display_mode()
        elif resource and hasattr(resource, "form_display_mode"):
            display_mode = resource.form_display_mode

        # Build form component
        await self._ensure_csrf_token(request)
        form_component = await self._build_form_component(
            resource,
            label,
            mode="create",
            user=user,
            errors=errors,
        )
        form_component._request = request

        # If HTMX request, always render as SlideOver
        if is_htmx:
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
                    class_="text-2xl font-bold text-gray-900 dark:text-white mt-2",
                ),
                class_="mb-6",
            ),
            el(
                "div",
                form_component,
                class_="bg-white dark:bg-gray-800 shadow rounded-lg p-6",
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
        is_htmx = request.headers.get("HX-Request") == "true"

        # Get form display mode from resource configuration
        display_mode = "slider"  # default for edit
        if resource and hasattr(resource, "get_form_display_mode"):
            display_mode = resource.get_form_display_mode()
        elif resource and hasattr(resource, "form_display_mode"):
            display_mode = resource.form_display_mode

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
        )
        form_component._request = request

        # If HTMX request, always render as SlideOver
        if is_htmx:
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
                    class_="text-2xl font-bold text-gray-900 dark:text-white mt-2",
                ),
                class_="mb-6",
            ),
            el(
                "div",
                form_component,
                class_="bg-white dark:bg-gray-800 shadow rounded-lg p-6",
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

    async def render_wizard(
        self,
        request,
        resource,
        steps: list[dict],
        action_url: str,
        submit_label: str = "Submit",
    ) -> HTMLResponse:
        """Render a multi-step wizard form driven by Alpine.js.

        Each step is defined by a dict with ``"title"`` and ``"fields"`` keys.
        Only the step whose index matches the Alpine ``currentStep`` variable
        is visible at any time.  Previous / Next buttons advance or retreat
        through the steps, and the final step shows a Submit button that POSTs
        the whole form to ``action_url``.  A step indicator line (e.g.
        "Step 2 of 4") is shown above the step body.

        Args:
            request: Incoming HTTP request.
            resource: Admin resource instance (used to build field components).
            steps: Step definitions.  Each item must be a dict with at minimum
                ``"title": str`` and ``"fields": list[str]`` keys.
            action_url: Form ``action`` / HTMX ``hx-post`` target URL.
            submit_label: Label for the submit button on the final step.

        Returns:
            ``HTMLResponse`` with the wizard form fragment or full page.
        """
        label = self.resource_name.replace("_", " ").title()
        total_steps = len(steps)

        # Build Alpine.js data initialiser - currentStep is 0-indexed.
        alpine_data = "{ currentStep: 0 }"

        step_els: list[Any] = []
        for idx, step_def in enumerate(steps):
            step_title = step_def.get("title", f"Step {idx + 1}")
            step_fields_names: list[str] = step_def.get("fields", [])

            # Attempt to render each named field via the field registry.
            field_html_parts: list[Any] = []
            if resource and resource.model:
                try:
                    from lexigram.admin.forms.components import FormSchemaGenerator

                    generator = FormSchemaGenerator()
                    schema = generator.from_pydantic(resource.model)
                    schema_map = {f.name: f for f in schema.fields}

                    for fname in step_fields_names:
                        field_schema = schema_map.get(fname)
                        if field_schema is None:
                            field_html_parts.append(
                                el(
                                    "p",
                                    f"Unknown field: {fname}",
                                    class_="text-xs text-red-500",
                                )
                            )
                            continue
                        field_component = self._create_field_component(
                            field_schema, field_schema.default
                        )
                        if field_component:
                            raw = field_component.render()
                            field_html_parts.append(
                                el("div", raw, class_="wizard-field mb-4")
                            )
                except AdminValidationError as exc:
                    logger.debug(
                        "render_wizard field generation failed resource=%s: %s",
                        self.resource_name,
                        exc,
                    )
                    field_html_parts.append(
                        el(
                            "p",
                            f"Error building fields: {exc}",
                            class_="text-red-500 text-sm",
                        )
                    )
            else:
                for fname in step_fields_names:
                    field_html_parts.append(
                        el(
                            "div",
                            el(
                                "input",
                                type="text",
                                name=fname,
                                placeholder=fname.replace("_", " ").title(),
                                class_=(
                                    "block w-full rounded-md border border-gray-300 "
                                    "dark:border-gray-600 bg-white dark:bg-gray-700 "
                                    "text-gray-900 dark:text-gray-100 px-3 py-2 text-sm "
                                    "focus:outline-none focus:ring-2 focus:ring-primary-500"
                                ),
                            ),
                            class_="wizard-field mb-4",
                        )
                    )

            # Navigation buttons
            nav_buttons: list[Any] = []
            if idx > 0:
                nav_buttons.append(
                    el(
                        "button",
                        "← Previous",
                        type="button",
                        class_=(
                            "px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 "
                            "border border-gray-300 dark:border-gray-600 rounded-lg "
                            "hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                        ),
                        **{"@click": "currentStep--"},
                    )
                )

            if idx < total_steps - 1:
                nav_buttons.append(
                    el(
                        "button",
                        "Next →",
                        type="button",
                        class_=(
                            "px-4 py-2 text-sm font-medium text-white bg-primary-600 "
                            "hover:bg-primary-700 rounded-lg focus:outline-none "
                            "focus:ring-2 focus:ring-primary-500 transition-colors"
                        ),
                        **{"@click": "currentStep++"},
                    )
                )
            else:
                nav_buttons.append(
                    el(
                        "button",
                        submit_label,
                        type="submit",
                        class_=(
                            "px-4 py-2 text-sm font-medium text-white bg-green-600 "
                            "hover:bg-green-700 rounded-lg focus:outline-none "
                            "focus:ring-2 focus:ring-green-500 transition-colors"
                        ),
                    )
                )

            step_indicator = el(
                "p",
                f"Step {idx + 1} of {total_steps}",
                class_="text-xs text-gray-500 dark:text-gray-400 mb-1",
            )
            step_heading = el(
                "h3",
                step_title,
                class_="text-base font-semibold text-gray-900 dark:text-gray-100 mb-4",
            )
            step_els.append(
                el(
                    "div",
                    step_indicator,
                    step_heading,
                    *field_html_parts,
                    el(
                        "div",
                        *nav_buttons,
                        class_="flex items-center justify-between mt-6 gap-3",
                    ),
                    class_="wizard-step",
                    **{"x-show": f"currentStep === {idx}"},
                )
            )

        # Progress bar / step dots
        step_dots: list[Any] = [
            el(
                "span",
                str(i + 1),
                class_=(
                    f"wizard-dot inline-flex items-center justify-center w-7 h-7 "
                    f"rounded-full text-xs font-semibold transition-colors "
                    f"{'bg-primary-600 text-white' if i == 0 else 'bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400'}"
                ),
                **{
                    ":class": (
                        f"currentStep === {i} "
                        f"? 'bg-primary-600 text-white' "
                        f": currentStep > {i} "
                        f"? 'bg-green-500 text-white' "
                        f": 'bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400'"
                    )
                },
            )
            for i in range(total_steps)
        ]
        progress_bar = el(
            "div",
            *step_dots,
            class_="wizard-progress flex items-center gap-2 mb-6",
        )

        form_el = el(
            "form",
            progress_bar,
            *step_els,
            action=action_url,
            method="post",
            class_="wizard-form",
            **{
                "x-data": alpine_data,
                "hx-post": action_url,
                "hx-target": "#main-content",
                "hx-swap": "innerHTML",
            },
        )

        is_htmx = request.headers.get("HX-Request") == "true"
        if is_htmx:
            return HTMLResponse(render_to_string(form_el))

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
                    class_="text-2xl font-bold text-gray-900 dark:text-white mt-2",
                ),
                class_="mb-6",
            ),
            el(
                "div",
                form_el,
                class_="bg-white dark:bg-gray-800 shadow rounded-lg p-6",
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
            elif (
                hasattr(resource, "_data_source")
                and resource._data_source
                and hasattr(resource._data_source, "find_one")
            ):
                item = await resource._data_source.find_one(item_id)
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
        session_id = request.session.get("admin_user_id", "")
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
            # Use the declared form class
            return form_class(initial=initial_data, action=action_url)

        # Generate form from Pydantic model
        if resource and resource.model:
            try:
                from lexigram.admin.forms.components import FormSchemaGenerator
                from lexigram.admin.forms.fields import FieldType

                generator = FormSchemaGenerator()
                schema = generator.from_pydantic(resource.model)

                # Populate relation field options from the related resource's data source
                for field_schema in schema.fields:
                    if field_schema.type == FieldType.BELONGS_TO:
                        related_resource_name = field_schema.related_resource
                        if related_resource_name and hasattr(resource, "_admin_registry"):
                            try:
                                related_resource_cls = resource._admin_registry.get(related_resource_name)
                                if related_resource_cls:
                                    related_instance = related_resource_cls()
                                    if hasattr(related_instance, "_data_source") and related_instance._data_source:
                                        ds = related_instance._data_source
                                        if hasattr(ds, "list_all"):
                                            records = await ds.list_all()
                                            field_schema.options = [
                                                {"value": str(getattr(r, "id", r)), "label": str(r)}
                                                for r in records
                                            ]
                            except Exception:
                                import logging
                                logging.getLogger(__name__).debug(
                                    "Failed to load options for %s.%s",
                                    self.resource_name,
                                    field_schema.name,
                                )

                # Build field components from schema
                field_components = []
                for field_schema in schema.fields:
                    # Skip auto-generated fields
                    if field_schema.name in ("id", "created_at", "updated_at"):
                        continue

                    # --- Field-level RBAC enforcement ---
                    if user:
                        if self._permission_service is not None:
                            _perm_svc = self._permission_service
                            # Hide field if user lacks view permission
                            if not _perm_svc.can_view_field(
                                user, self.resource_name, field_schema.name
                            ):
                                continue
                            # Mark field non-editable if user lacks edit permission
                            if mode == "edit" and not _perm_svc.can_edit_field(
                                user, self.resource_name, field_schema.name
                            ):
                                field_schema.editable = False
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
                            field_component.errors = errors[field_schema.name]
                        field_components.append(field_component.render())

                submit_label = "Update" if mode == "edit" else "Create"

                # Create Form component with fields
                form = Form(
                    action_url=action_url,
                    method="post",
                    submit_label=submit_label,
                    hx_target="#main-content",
                    hx_swap="innerHTML",
                )
                form.children = field_components
                return form

            except AdminValidationError as e:
                logger.debug(
                    "Failed to generate form for %s: %s",
                    self.resource_name,
                    e,
                )
                return el("p", f"Error generating form: {e}", class_="text-red-500")

        return el(
            "p",
            "No form configuration available for this resource.",
            class_="text-gray-500",
        )

    def _create_field_component(self, field_schema, value) -> Any:
        """Create a field component from a FieldSchema.

        Args:
            field_schema: The field schema definition
            value: Initial value for the field

        Returns:
            Field component instance
        """
        from lexigram.admin.resources.field_renderer import _field_renderer_registry

        common_args = {
            "label": field_schema.label,
            "required": field_schema.required,
            "disabled": not field_schema.editable,
            "help_text": field_schema.help_text,
            "default": field_schema.default,
            "placeholder": field_schema.placeholder,
            "name": field_schema.name,
        }

        # Use registry to get the appropriate renderer and field instance
        renderer = _field_renderer_registry.get_renderer(
            field_schema.type,
            field_schema,
        )
        return renderer.render_field(field_schema, value, common_args).bind(value)


__all__ = ["FormRenderer"]
