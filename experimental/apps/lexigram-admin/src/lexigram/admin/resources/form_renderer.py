from __future__ import annotations

"""Form rendering for admin resources."""

import inspect
from typing import Any

from starlette.responses import HTMLResponse

from lexigram.admin.auth.services.csrf_service import AdminCsrfService
from lexigram.admin.config import AdminConfig
from lexigram.admin.engine.renderer import AdminRenderer
from lexigram.admin.exceptions import AdminValidationError
from lexigram.admin.rbac.service import PermissionService
from lexigram.admin.resources.data_access import get_resource_data_source
from lexigram.admin.resources.urls import admin_prefix_from_request
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
    try:
        if callable(getter):
            mode = getter()
        else:
            mode = getattr(resource, "form_display_mode", None)
    except Exception:  # noqa: BLE001 — malformed presentation config is non-fatal
        logger.exception("admin.form_display_mode_resolution_failed")
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
        data: dict[str, Any] | None = None,
    ) -> HTMLResponse:
        """Render create form using Modal/SlideOver components based on form_display_mode."""
        label = self.resource_name.replace("_", " ").title()
        if user is None:
            try:
                user = getattr(request.state, "user", None)
            except (AttributeError, KeyError):
                user = None

        # Check if HTMX request (for modal/slider loading)
        is_htmx = wants_fragment(request)
        admin_prefix = admin_prefix_from_request(request)

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

        # Build form component. Resolve the mounted PermissionService lazily
        # from app state as well as accepting an explicit service. The mounted
        # authorization middleware stores a CRUD capability dictionary in
        # request.state.permissions, which is deliberately not treated as a
        # field-permission service.
        await self._ensure_csrf_token(request)
        permission_service = self._permission_service or self._request_permission_service(
            request
        )
        form_component = await self._build_form_component(
            resource,
            label,
            mode="create",
            initial_data=data,
            data=data,
            user=user,
            errors=errors,
            permission_service=permission_service,
            admin_prefix=admin_prefix,
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
                    href=f"{admin_prefix}/{self.resource_name}",
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
                {"label": "Dashboard", "url": admin_prefix},
                {"label": label, "url": f"{admin_prefix}/{self.resource_name}"},
                {
                    "label": "Create",
                    "url": f"{admin_prefix}/{self.resource_name}/create",
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
        data: dict[str, Any] | None = None,
    ) -> HTMLResponse:
        """Render edit form using Modal/SlideOver components based on form_display_mode."""
        label = self.resource_name.replace("_", " ").title()
        if user is None:
            try:
                user = getattr(request.state, "user", None)
            except (AttributeError, KeyError):
                user = None

        # Check if HTMX request (for modal/slide-over loading)
        is_htmx = wants_fragment(request)
        admin_prefix = admin_prefix_from_request(request)

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

        # On a failed submission, submitted values must win over the
        # persisted record so validation does not reset the user's inputs.
        if data is not None:
            initial_data = {**initial_data, **data}

        # Build form component with initial data. See render_create for why
        # permissions are resolved from app state instead of request.state.
        await self._ensure_csrf_token(request)
        permission_service = self._permission_service or self._request_permission_service(
            request
        )
        form_component = await self._build_form_component(
            resource,
            label,
            mode="edit",
            initial_data=initial_data,
            data=data,
            record_id=item_id,
            user=user,
            errors=errors,
            permission_service=permission_service,
            admin_prefix=admin_prefix,
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
                    href=f"{admin_prefix}/{self.resource_name}/{item_id}",
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
                {"label": "Dashboard", "url": admin_prefix},
                {"label": label, "url": f"{admin_prefix}/{self.resource_name}"},
                {
                    "label": f"#{item_id}",
                    "url": f"{admin_prefix}/{self.resource_name}/{item_id}",
                },
                {
                    "label": "Edit",
                    "url": f"{admin_prefix}/{self.resource_name}/{item_id}/edit",
                },
            ],
        )

    @staticmethod
    def _record_to_mapping(record: Any) -> dict[str, Any]:
        """Normalize common data-source record shapes for form defaults."""
        if isinstance(record, dict):
            return dict(record)
        model_dump = getattr(record, "model_dump", None)
        if callable(model_dump):
            dumped = model_dump()
            if isinstance(dumped, dict):
                return dumped
        try:
            values = vars(record)
        except TypeError:
            values = {
                name: getattr(record, name)
                for name in dir(record)
                if not name.startswith("_") and not callable(getattr(record, name, None))
            }
        return dict(values) if isinstance(values, dict) else {}

    async def _fetch_item_data(self, resource, item_id: str) -> dict:
        """Fetch existing item data for edit mode."""
        initial_data: dict[str, Any] = {}
        try:
            # Resolve the canonical source first. A legacy ``service`` may
            # still be present for compatibility, but must not shadow a
            # mounted modern data source during edit rendering.
            data_source = get_resource_data_source(resource)
            if data_source is None or not hasattr(data_source, "find_one"):
                return initial_data
            item = await data_source.find_one(item_id)
            if item is not None:
                initial_data = self._record_to_mapping(item)
        except Exception as e:  # noqa: BLE001 — edit rendering degrades to an empty form
            logger.debug(
                "Failed to get item %s/%s for edit: %s",
                self.resource_name,
                item_id,
                e,
            )
        return initial_data

    @staticmethod
    def _request_permission_service(request: Any) -> Any | None:
        """Return a real field-permission service exposed by the mount.

        ``request.state.permissions`` is intentionally ignored: the normal
        mounted authorization middleware puts a CRUD capability mapping
        there, and accepting it here would turn a dictionary into a service
        only after an AttributeError at render time. The bundle exposes the
        singleton on the inner admin app state instead.
        """
        try:
            app = request.app
        except (AttributeError, KeyError):
            app = None
        service = getattr(getattr(app, "state", None), "permission_service", None)
        if service is not None and callable(getattr(service, "can_view_field", None)):
            return service
        try:
            request_state = request.state
        except (AttributeError, KeyError):
            request_state = None

        # Read only explicitly stored state values. ``MagicMock``-backed unit
        # scopes manufacture every missing attribute and would otherwise look
        # like a permission service, masking every form field.
        state_service = None
        if isinstance(request_state, dict):
            state_service = request_state.get("permission_service")
        else:
            state_storage = getattr(request_state, "_state", None)
            if isinstance(state_storage, dict):
                state_service = state_storage.get("permission_service")
            if state_service is None:
                try:
                    state_service = vars(request_state).get("permission_service")
                except TypeError:
                    state_service = None
        if state_service is not None and callable(
            getattr(state_service, "can_view_field", None)
        ):
            return state_service
        return None

    async def _field_permission(
        self,
        permission_service: Any,
        method_name: str,
        user: Any,
        field_name: str,
    ) -> bool:
        """Evaluate a field permission and fail closed on service errors."""
        try:
            result = getattr(permission_service, method_name)(
                user, self.resource_name, field_name
            )
            if inspect.isawaitable(result):
                result = await result
            return bool(result)
        except Exception:  # noqa: BLE001 — a broken authorization check must not leak fields
            logger.exception(
                "admin.resource_field_permission_check_failed",
                resource=self.resource_name,
                field=field_name,
                check=method_name,
            )
            return False

    async def _field_masked(
        self,
        permission_service: Any,
        user: Any,
        field_name: str,
    ) -> bool:
        """Evaluate masking policy and fail closed if it cannot be checked."""
        checker = getattr(permission_service, "should_mask_field", None)
        if not callable(checker):
            return False
        try:
            result = checker(user, self.resource_name, field_name)
            if inspect.isawaitable(result):
                result = await result
            return bool(result)
        except Exception:  # noqa: BLE001 — masking must fail closed
            logger.exception(
                "admin.resource_field_mask_check_failed",
                resource=self.resource_name,
                field=field_name,
            )
            return True

    async def _apply_declared_field_permissions(
        self,
        form: Any,
        user: Any,
        permission_service: Any | None,
    ) -> None:
        """Apply view/edit authorization to an instance-local declared form."""
        if user is None or permission_service is None:
            return
        fields = getattr(form, "fields", None)
        if not isinstance(fields, dict):
            return
        from dataclasses import replace as dc_replace

        for name, field_schema in list(fields.items()):
            if await self._field_masked(permission_service, user, name):
                fields[name] = dc_replace(field_schema, visible_in_form=False)
                continue
            if not await self._field_permission(
                permission_service, "can_view_field", user, name
            ):
                # Keep the node in place but mark it invisible: declared
                # layouts can still reference it without rendering a false
                # "field not found" diagnostic.
                fields[name] = dc_replace(field_schema, visible_in_form=False)
                continue
            if not await self._field_permission(
                permission_service, "can_edit_field", user, name
            ):
                fields[name] = dc_replace(field_schema, readonly=True)

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
        data: dict | None = None,
        record_id: str | None = None,
        user=None,
        errors: dict[str, list[str]] | None = None,
        permission_service: Any | None = None,
        admin_prefix: str | None = None,
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
        prefix = (admin_prefix or self._config.prefix).rstrip("/")

        # Determine form action URL
        if mode == "edit" and record_id:
            action_url = f"{prefix}/{self.resource_name}/{record_id}/edit"
        else:
            action_url = f"{prefix}/{self.resource_name}/create"

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
                data=data if data is not None else None,
                initial=initial_data,
                action=action_url,
                form_id=f"{self.resource_name}-{mode}-form",
                submit_label=submit_label,
                suppress_submit=in_slide_over,
                hx_post=action_url if htmx_enabled else None,
                hx_target=overlay_target if htmx_enabled else None,
                hx_swap="innerHTML",
            )
            await self._apply_declared_field_permissions(
                form, user, permission_service
            )
            await self._populate_form_relation_options(
                form,
                user=user,
                permission_service=permission_service,
            )
            if errors:
                form.errors.update(errors)
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
                await self._populate_relation_options(
                    schema,
                    user=user,
                    permission_service=permission_service,
                )

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
                    if user is not None:
                        if permission_service is not None:
                            _perm_svc = permission_service
                            # Masked fields must not be sent to the browser,
                            # including as edit-form defaults.
                            if await self._field_masked(
                                _perm_svc,
                                user,
                                field_schema.name,
                            ):
                                continue
                            # Hide field if user lacks view permission.
                            if not await self._field_permission(
                                _perm_svc,
                                "can_view_field",
                                user,
                                field_schema.name,
                            ):
                                continue
                            # A create form also writes field values; it must
                            # not expose a control that the caller cannot set.
                            if mode in {"create", "edit"} and not await self._field_permission(
                                _perm_svc,
                                "can_edit_field",
                                user,
                                field_schema.name,
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
                        errors=errors.get(field_schema.name) if errors else None,
                        admin_prefix=prefix,
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

                global_errors = [
                    message
                    for name, messages in (errors or {}).items()
                    if name in {"__all__", "__root__"}
                    for message in messages
                ]
                if global_errors:
                    body_fields.insert(
                        0,
                        el(
                            "div",
                            *[el("p", message) for message in global_errors],
                            role="alert",
                            class_="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive",
                        ),
                    )

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
        if not isinstance(entry, type):
            return entry
        try:
            return entry()
        except Exception:  # noqa: BLE001 — an unconstructable sibling is not fatal to this form
            logger.debug(
                "Failed to construct related resource %s for %s",
                resource_name,
                self.resource_name,
            )
            return entry

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

    async def _relation_options_allowed(
        self,
        related: Any,
        field_name: str,
        user: Any,
        permission_service: Any | None,
    ) -> bool:
        """Check access before embedding related records in a form.

        Relation options are rendered into the parent form HTML, so protecting
        only the separate ``relation-options`` endpoint is insufficient. A
        caller must be able to view the parent field and the related resource
        before its records are loaded here.
        """
        if user is None:
            return True
        if permission_service is not None and not await self._field_permission(
            permission_service,
            "can_view_field",
            user,
            field_name,
        ):
            return False
        if isinstance(related, type):
            return False
        checker = getattr(related, "has_view_permission", None)
        if callable(checker):
            try:
                result = checker(user)
                if inspect.isawaitable(result):
                    result = await result
                if not result:
                    return False
            except Exception:  # noqa: BLE001 — relation access must fail closed
                logger.exception(
                    "admin.related_resource_permission_check_failed",
                    resource=self.resource_name,
                    field=field_name,
                )
                return False
        if permission_service is not None:
            checker = getattr(permission_service, "can_view", None)
            if callable(checker):
                try:
                    result = checker(user, getattr(related, "name", ""))
                    if inspect.isawaitable(result):
                        result = await result
                    if not result:
                        return False
                except Exception:  # noqa: BLE001 — relation access must fail closed
                    logger.exception(
                        "admin.related_permission_service_check_failed",
                        resource=self.resource_name,
                        field=field_name,
                    )
                    return False
        return True

    async def _populate_form_relation_options(
        self,
        form: Any,
        user: Any = None,
        permission_service: Any | None = None,
    ) -> None:
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
            if not getattr(field_schema, "visible_in_form", True):
                continue
            related = self._resolve_related_resource(field_schema.resource)
            if not await self._relation_options_allowed(
                related, name, user, permission_service
            ):
                continue
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

    async def _populate_relation_options(
        self,
        schema: Any,
        user: Any = None,
        permission_service: Any | None = None,
    ) -> None:
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
            if not getattr(field_schema, "visible_in_form", True):
                continue
            related = self._resolve_related_resource(field_schema.resource)
            if not await self._relation_options_allowed(
                related, field_schema.name, user, permission_service
            ):
                continue
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
        try:
            if callable(getter):
                sections = getter()
                if sections is not None:
                    return list(sections)
            return list(getattr(resource, "form_sections", ()) or ())
        except Exception:  # noqa: BLE001 — malformed layout falls back to flat fields
            logger.exception("admin.form_sections_resolution_failed")
            return []

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

    def _create_field_component(
        self,
        field_schema,
        value,
        errors: list[str] | None = None,
        admin_prefix: str | None = None,
    ) -> Any:
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
            "error": errors,
        }
        # Searchable relation selects load options over HTMX from the related
        # resource's registered relation-options endpoint.
        related_resource = getattr(field_schema, "resource", None)
        if getattr(field_schema, "searchable", False) and related_resource:
            prefix = (admin_prefix or self._config.prefix).rstrip("/")
            common_args["relation_options_url"] = (
                f"{prefix}/{related_resource}/relation-options"
            )

        # Use registry to get the appropriate renderer and field instance
        renderer = _field_renderer_registry.get_renderer(field_schema)
        return renderer.render_field(field_schema, value, common_args)


__all__ = ["FormRenderer"]
