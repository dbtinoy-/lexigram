"""Record-level CRUD action handlers for Admin Resources.

List / detail / create / edit / clone / restore / purge / delete flows,
plus the form-data coercion helpers they share. Specialized handlers
(import, user permissions, bulk) live in :mod:`.handler`.
"""

from __future__ import annotations

from collections.abc import Mapping
import inspect
from typing import Any, Protocol, get_type_hints

from starlette.requests import Request as StarletteRequest
from starlette.responses import HTMLResponse

from lexigram.admin.config import AdminConfig
from lexigram.admin.exceptions import PermissionDeniedError
from lexigram.admin.resources.data_access import get_resource_data_source
from lexigram.admin.resources.form_coercion import (
    _validation_errors_to_dict,
)
from lexigram.admin.resources.form_guard import (
    PROTECTED_FORM_FIELDS,
    sanitize_form_data,
)
from lexigram.admin.resources.urls import (
    admin_prefix_from_request,
    admin_url,
)
from lexigram.logging import get_logger

__all__ = [
    "CloneActionHandler",
    "CreateActionHandler",
    "DeleteActionHandler",
    "DetailActionHandler",
    "EditActionHandler",
    "ImportActionHandler",
    "InlineMutationActionHandler",
    "ListActionHandler",
    "PurgeActionHandler",
    "RelationOptionsActionHandler",
    "ResourceActionHandler",
    "RestoreActionHandler",
]

logger = get_logger(__name__)


async def _maybe_await(value: Any) -> Any:
    """Resolve sync and async resource/action hooks uniformly."""
    return await value if inspect.isawaitable(value) else value


async def _call_permission_hook(
    hook: Any,
    value: Any,
) -> bool:
    """Evaluate a record permission hook, failing closed on hook errors."""
    try:
        return bool(await _maybe_await(hook(value)))
    except Exception:  # noqa: BLE001 — authorization must fail closed
        logger.exception("admin.resource_permission_hook_failed")
        return False


def _request_permission_service(request: StarletteRequest) -> Any | None:
    """Resolve the mounted field-permission service without using capabilities."""
    try:
        app = request.app
    except (AttributeError, KeyError):
        app = None
    service = getattr(getattr(app, "state", None), "permission_service", None)
    if service is not None and callable(getattr(service, "can_edit_field", None)):
        return service
    try:
        request_state = request.state
    except (AttributeError, KeyError, RuntimeError):
        request_state = None
    # Only read explicitly stored state values. Some minimal test requests use
    # MagicMock for ``state``; fabricated attributes must not become an
    # authorization service and accidentally turn masking on for every field.
    if isinstance(request_state, dict):
        state_service = request_state.get("permission_service")
    else:
        storage = getattr(request_state, "_state", None)
        if isinstance(storage, dict):
            state_service = storage.get("permission_service")
        else:
            try:
                state_service = vars(request_state).get("permission_service")
            except TypeError:
                state_service = None
    if state_service is not None and callable(
        getattr(state_service, "can_edit_field", None)
    ):
        return state_service
    return None


async def _field_permission_allowed(
    request: StarletteRequest,
    resource: Any,
    field_name: str,
    method_name: str,
) -> bool:
    """Evaluate a mounted field permission and fail closed on service errors."""
    service = _request_permission_service(request)
    if service is None:
        return True
    checker = getattr(service, method_name, None)
    if not callable(checker):
        return True
    try:
        user = getattr(request.state, "user", None)
    except (AttributeError, KeyError):
        user = None
    try:
        allowed = await _maybe_await(
            checker(user, resource.name or "", field_name)
        )
    except Exception:  # noqa: BLE001 — authorization must fail closed
        logger.exception(
            "admin.resource_field_permission_check_failed",
            resource=getattr(resource, "name", None),
            field=field_name,
            check=method_name,
        )
        return False
    return bool(allowed)


async def _field_edit_allowed(
    request: StarletteRequest,
    resource: Any,
    field_name: str,
) -> bool:
    """Return whether the mounted permission service allows a field write."""
    return await _field_permission_allowed(
        request, resource, field_name, "can_edit_field"
    )


async def _field_view_allowed(
    request: StarletteRequest,
    resource: Any,
    field_name: str,
) -> bool:
    """Return whether the submitted field is visible to the caller."""
    return await _field_permission_allowed(
        request, resource, field_name, "can_view_field"
    )


async def _field_masked(
    request: StarletteRequest,
    resource: Any,
    field_name: str,
) -> bool:
    """Return whether the field value must be hidden from this request."""
    service = _request_permission_service(request)
    checker = getattr(service, "should_mask_field", None)
    if service is None or not callable(checker):
        return False
    user = getattr(getattr(request, "state", None), "user", None)
    try:
        result = checker(user, resource.name or "", field_name)
        return bool(await _maybe_await(result))
    except Exception:  # noqa: BLE001 — masking fails closed
        logger.exception(
            "admin.resource_field_mask_check_failed",
            resource=getattr(resource, "name", None),
            field=field_name,
        )
        return True


async def _authorize_form_fields(
    request: StarletteRequest,
    resource: Any,
    data: dict[str, Any],
) -> HTMLResponse | None:
    """Reject submitted values for fields the caller cannot edit.

    Rendering a field as readonly is only a UX measure. This check is the
    server-side boundary that prevents a crafted POST from writing a hidden or
    readonly field. It deliberately ignores ``request.state.permissions``;
    that value is a CRUD capability mapping in the mounted middleware.
    """
    for field_name in data:
        if not await _field_view_allowed(request, resource, field_name):
            return HTMLResponse("Forbidden", status_code=403)
        if not await _field_edit_allowed(request, resource, field_name):
            return HTMLResponse("Forbidden", status_code=403)
    return None


def _sanitize_submitted_form_data(
    resource: Any,
    data: dict[str, Any],
) -> dict[str, Any]:
    """Apply the resource's mass-assignment boundary before custom hooks.

    ``before_validate`` is intentionally overridable. Sanitizing the raw
    request first prevents a custom validation implementation from accidentally
    reintroducing client-supplied IDs, tenant keys, hidden fields, or unknown
    model fields before its output reaches ``before_create``/``before_update``.
    Hook-added server values remain supported because only the untrusted input
    is sanitized here.
    """
    protected_fields = set(
        getattr(resource, "protected_form_fields", PROTECTED_FORM_FIELDS)
    )
    protected_fields.update(getattr(resource, "form_exclude_fields", ()) or ())
    protected_fields.update(getattr(resource, "readonly_fields", ()) or ())

    declared_fields = {
        str(getattr(field, "name", ""))
        for field in (getattr(resource, "fields", ()) or ())
        if getattr(field, "name", None)
    }
    form_getter = getattr(resource, "get_form_class", None)
    form_class = None
    try:
        form_class = form_getter() if callable(form_getter) else getattr(resource, "form_class", None)
    except Exception:  # noqa: BLE001 — validation/rendering will report config errors
        form_class = None
    declared_form_fields = getattr(form_class, "_declared_fields", None)
    if isinstance(declared_form_fields, dict):
        declared_fields.update(str(name) for name in declared_form_fields)
        protected_fields.update(
            str(name)
            for name, field in declared_form_fields.items()
            if not getattr(field, "visible_in_form", True)
            or getattr(field, "readonly", False)
        )
    protected_fields.update(
        str(getattr(field, "name", ""))
        for field in (getattr(resource, "fields", ()) or ())
        if getattr(field, "name", None)
        and (
            not getattr(field, "visible_in_form", True)
            or getattr(field, "readonly", False)
        )
    )

    allow_extra_fields = bool(getattr(resource, "form_allow_extra_fields", False))
    cleaned = sanitize_form_data(
        data,
        model=getattr(resource, "model", None),
        protected_fields=protected_fields,
        allow_extra_fields=allow_extra_fields,
    )
    if getattr(resource, "model", None) is None and declared_fields and not allow_extra_fields:
        cleaned = {
            key: value
            for key, value in cleaned.items()
            if key in declared_fields and key not in protected_fields
        }
    return cleaned


def _normalize_validation_result(
    validation: Any,
) -> tuple[dict[str, Any] | None, dict[str, list[str]] | None]:
    """Normalize Resource hook results while keeping legacy overrides usable."""
    if isinstance(validation, Mapping):
        return dict(validation), None
    if not callable(getattr(validation, "is_err", None)):
        return None, {"__all__": ["before_validate must return a validation result"]}
    try:
        if validation.is_err():
            return None, _validation_errors_to_dict(validation.unwrap_err())
        data = validation.unwrap()
        if not isinstance(data, Mapping):
            return None, {"__all__": ["before_validate must return a mapping"]}
        return dict(data), None
    except Exception as exc:  # noqa: BLE001 — malformed custom hooks re-render safely
        errors = _validation_errors_from_exception(exc)
        return None, errors or {"__all__": ["Form validation failed"]}


def _record_to_mapping(record: Any) -> dict[str, Any]:
    """Normalize a data-source record before validating an edit patch."""
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
        return {}
    return dict(values) if isinstance(values, dict) else {}


def _validation_errors_from_exception(exc: Exception) -> dict[str, list[str]] | None:
    """Map expected hook/data validation failures back to form fields."""
    from lexigram.admin.exceptions import AdminValidationError, ConflictError

    if isinstance(exc, AdminValidationError):
        return _validation_errors_to_dict(exc)
    if isinstance(exc, ConflictError):
        return {"__all__": [str(getattr(exc, "message", None) or exc)]}

    # Pydantic ValidationError and compatible adapters expose ``errors()``.
    errors_method = getattr(exc, "errors", None)
    if callable(errors_method):
        try:
            result: dict[str, list[str]] = {}
            for error in errors_method():
                location = error.get("loc") or ("__all__",)
                field = str(location[0])
                result.setdefault(field, []).append(str(error.get("msg", exc)))
            if result:
                return result
        except (AttributeError, TypeError, ValueError):
            pass

    if isinstance(exc, (TypeError, ValueError)):
        return {"__all__": [str(exc) or "Form validation failed"]}
    return None


async def _render_create_validation_error(
    form_renderer: Any,
    request: StarletteRequest,
    resource: Any,
    data: dict[str, Any],
    errors: dict[str, list[str]],
) -> Any:
    """Render a create form error with the HTTP status expected by clients."""
    response = await form_renderer.render_create(
        request,
        resource,
        user=getattr(getattr(request, "state", None), "user", None),
        errors=errors,
        data=data,
    )
    response.status_code = 422
    return response


async def _render_edit_validation_error(
    form_renderer: Any,
    request: StarletteRequest,
    resource: Any,
    item_id: str,
    data: dict[str, Any],
    errors: dict[str, list[str]],
) -> Any:
    """Render an edit form error with the HTTP status expected by clients."""
    response = await form_renderer.render_edit(
        request,
        resource,
        item_id,
        user=getattr(getattr(request, "state", None), "user", None),
        errors=errors,
        data=data,
    )
    response.status_code = 422
    return response


def _mutation_redirect(
    request: StarletteRequest,
    url: str,
    message: str,
) -> Any:
    """Return a redirect that works for both native and HTMX mutations.

    A plain 302 is followed inside HTMX's XHR and can replace the current
    table with a full page. ``HX-Redirect`` tells HTMX to perform a real
    browser navigation while preserving the native POST/DELETE fallback.
    """
    from starlette.responses import RedirectResponse

    if request.headers.get("HX-Request") == "true":
        import json

        response = HTMLResponse("")
        response.headers["HX-Redirect"] = url
        response.headers["HX-Trigger"] = json.dumps(
            {"show-toast": {"message": message, "type": "success"}}
        )
        return response
    return RedirectResponse(url=url, status_code=302)


def _form_data_dict(form: Any) -> dict[str, Any]:
    """Convert form data while preserving repeated controls.

    ``dict(FormData)`` keeps only the last value for a repeated key, which
    drops selections from ``<select multiple>`` and has-many relation fields.
    Keep repeated values as a list so the resource coercion and form schemas
    can validate them instead of silently losing user input.
    """
    items = form.multi_items() if hasattr(form, "multi_items") else form.items()
    data: dict[str, Any] = {}
    for raw_key, value in items:
        # Native multi-select/checkbox widgets conventionally submit
        # ``field[]``. Normalize that transport suffix before model/form
        # validation so the declared field receives every selected value.
        key = str(raw_key)
        if key.endswith("[]"):
            key = key[:-2]
        if key not in data:
            data[key] = value
        elif isinstance(data[key], list):
            data[key].append(value)
        else:
            data[key] = [data[key], value]
    return data


class ResourceActionHandler(Protocol):
    """Protocol for action handlers."""

    def can_handle(self, action: str) -> bool: ...

    async def handle(
        self, request: StarletteRequest, resource: Any, **kwargs: Any
    ) -> Any: ...


class ListActionHandler:
    def __init__(self, list_renderer: Any):
        self.list_renderer = list_renderer

    def can_handle(self, action: str) -> bool:
        return action == "list"

    async def handle(
        self, request: StarletteRequest, resource: Any, **kwargs: Any
    ) -> Any:
        return await self.list_renderer.render(request, resource)


class DetailActionHandler:
    def __init__(self, detail_renderer: Any):
        self.detail_renderer = detail_renderer

    def can_handle(self, action: str) -> bool:
        return action == "detail"

    async def handle(
        self, request: StarletteRequest, resource: Any, **kwargs: Any
    ) -> Any:
        item_id = request.path_params.get("id", "?")
        data_source = get_resource_data_source(resource)
        if data_source is not None and hasattr(data_source, "find_one"):
            try:
                if await data_source.find_one(item_id) is None:
                    return HTMLResponse("Not found", status_code=404)
            except (AttributeError, TypeError, ValueError, RuntimeError) as exc:
                logger.exception("admin.detail_lookup_failed", error=str(exc))
                return HTMLResponse("Unable to load record", status_code=503)
        return await self.detail_renderer.render_detail(
            request,
            resource,
            item_id,
            user=getattr(getattr(request, "state", None), "user", None),
        )


class CreateActionHandler:
    def __init__(self, form_renderer: Any):
        self.form_renderer = form_renderer

    def can_handle(self, action: str) -> bool:
        return action == "create"

    async def handle(
        self, request: StarletteRequest, resource: Any, **kwargs: Any
    ) -> Any:
        request_user = getattr(getattr(request, "state", None), "user", None)
        if request.method == "POST":
            return await self._handle_create(request, resource)
        return await self.form_renderer.render_create(
            request,
            resource,
            user=request_user,
        )

    async def _handle_create(self, request: StarletteRequest, resource: Any) -> Any:
        from lexigram.admin.resources.base import Resource

        form = (
            request.scope["admin_form_data"]
            if "admin_form_data" in request.scope
            else await request.form()
        )
        data = _form_data_dict(form)
        data.pop("csrf_token", None)

        data_source = get_resource_data_source(resource)
        if isinstance(resource, Resource) and data_source is not None:
            data = _sanitize_submitted_form_data(resource, data)
            field_error = await _authorize_form_fields(request, resource, data)
            if field_error is not None:
                return field_error
            try:
                validation = await resource.before_validate(data)
            except Exception as exc:  # noqa: BLE001 — validation failures re-render safely
                errors = _validation_errors_from_exception(exc)
                if errors is not None:
                    return await _render_create_validation_error(
                        self.form_renderer, request, resource, data, errors
                    )
                logger.exception("admin.before_validate_create_failed")
                return HTMLResponse("Unable to validate form", status_code=500)
            validated_data, validation_errors = _normalize_validation_result(validation)
            if validation_errors is not None:
                return await _render_create_validation_error(
                    self.form_renderer,
                    request,
                    resource,
                    data,
                    validation_errors,
                )
            assert validated_data is not None
            try:
                validated = await resource.before_create(validated_data)
                if not isinstance(validated, Mapping):
                    raise TypeError("before_create must return a mapping")
                record = await data_source.create(dict(validated))
            except (PermissionError, PermissionDeniedError):
                return HTMLResponse("Forbidden", status_code=403)
            except NotImplementedError:
                return HTMLResponse("Resource does not support create", status_code=503)
            except Exception as exc:  # noqa: BLE001 — validation/storage errors are sanitized
                errors = _validation_errors_from_exception(exc)
                if errors is not None:
                    return await _render_create_validation_error(
                        self.form_renderer, request, resource, data, errors
                    )
                logger.exception("admin.create_failed")
                return HTMLResponse("Unable to create record", status_code=503)
            if record is None:
                return HTMLResponse("Unable to create record", status_code=503)
            try:
                await _maybe_await(resource.after_create(record))
            except Exception:  # noqa: BLE001 — record is already persisted
                logger.exception("admin.after_create_failed")
                return HTMLResponse(
                    "Record created, but finalization failed", status_code=500
                )

            from starlette.responses import RedirectResponse

            url = admin_url(
                admin_prefix_from_request(request),
                resource.name or "",
            )
            if request.headers.get("HX-Request") == "true":
                response = HTMLResponse("")
                response.headers["HX-Redirect"] = url
                response.headers["HX-Trigger"] = (
                    '{"show-toast":{"message":"Created successfully","type":"success"}}'
                )
                return response
            return RedirectResponse(url=url, status_code=302)

        if request.method == "POST":
            return HTMLResponse("Resource data source unavailable", status_code=503)
        return await self.form_renderer.render_create(
            request,
            resource,
            user=getattr(getattr(request, "state", None), "user", None),
        )


class EditActionHandler:
    def __init__(self, form_renderer: Any):
        self.form_renderer = form_renderer

    def can_handle(self, action: str) -> bool:
        return action == "edit"

    async def handle(
        self, request: StarletteRequest, resource: Any, **kwargs: Any
    ) -> Any:
        item_id = request.path_params.get("id", "?")
        request_user = getattr(getattr(request, "state", None), "user", None)
        if request.method == "POST":
            return await self._handle_update(request, resource, item_id)
        data_source = get_resource_data_source(resource)
        if data_source is not None and hasattr(data_source, "find_one"):
            try:
                if await data_source.find_one(item_id) is None:
                    return HTMLResponse("Not found", status_code=404)
            except (AttributeError, TypeError, ValueError, RuntimeError) as exc:
                logger.exception("admin.edit_lookup_failed", error=str(exc))
                return HTMLResponse("Unable to load record", status_code=503)
        return await self.form_renderer.render_edit(
            request,
            resource,
            item_id,
            user=request_user,
        )

    async def _handle_update(
        self, request: StarletteRequest, resource: Any, item_id: str
    ) -> Any:
        from lexigram.admin.resources.base import Resource

        form = (
            request.scope["admin_form_data"]
            if "admin_form_data" in request.scope
            else await request.form()
        )
        data = _form_data_dict(form)
        data.pop("csrf_token", None)

        data_source = get_resource_data_source(resource)
        if isinstance(resource, Resource) and data_source is not None:
            data = _sanitize_submitted_form_data(resource, data)
            try:
                record = await data_source.find_one(item_id)
            except Exception as exc:  # noqa: BLE001 — storage failures are not form errors
                logger.exception("admin.edit_lookup_failed", error=str(exc))
                return HTMLResponse("Unable to load record", status_code=503)
            if record is None:
                return HTMLResponse("Not found", status_code=404)
            can_update = getattr(resource, "can_update", None)
            if can_update and not await _call_permission_hook(can_update, record):
                return HTMLResponse("This record cannot be updated", status_code=403)

            field_error = await _authorize_form_fields(request, resource, data)
            if field_error is not None:
                return field_error

            # Validate the complete candidate record. Edit forms can omit
            # disabled/hidden fields, so validating the raw patch would report
            # false "field required" errors and would make readonly fields
            # impossible to edit around. The guard still strips protected
            # values before the update hook/data source sees them.
            candidate = {**_record_to_mapping(record), **data}
            try:
                validation = await resource.before_validate(candidate)
            except Exception as exc:  # noqa: BLE001 — validation failures re-render safely
                errors = _validation_errors_from_exception(exc)
                if errors is not None:
                    return await _render_edit_validation_error(
                        self.form_renderer, request, resource, item_id, data, errors
                    )
                logger.exception("admin.before_validate_edit_failed")
                return HTMLResponse("Unable to validate form", status_code=500)
            validated_data, validation_errors = _normalize_validation_result(validation)
            if validation_errors is not None:
                return await _render_edit_validation_error(
                    self.form_renderer,
                    request,
                    resource,
                    item_id,
                    data,
                    validation_errors,
                )
            assert validated_data is not None
            # Validate against the complete candidate for required-field and
            # cross-field checks, but persist only submitted changes. Passing
            # the entire record to ``update`` would re-write stale values and
            # could cause lost updates under concurrent edits. Hooks receive a
            # patch and may add server-managed keys such as ``updated_at``.
            existing_data = _record_to_mapping(record)
            update_data = {
                key: value
                for key, value in validated_data.items()
                if key in data or key not in existing_data
            }
            try:
                validated = await resource.before_update(item_id, update_data)
                if not isinstance(validated, Mapping):
                    raise TypeError("before_update must return a mapping")
                updated_record = await data_source.update(item_id, dict(validated))
            except (PermissionError, PermissionDeniedError):
                return HTMLResponse("Forbidden", status_code=403)
            except NotImplementedError:
                return HTMLResponse("Resource does not support update", status_code=503)
            except Exception as exc:  # noqa: BLE001 — validation/storage errors are sanitized
                errors = _validation_errors_from_exception(exc)
                if errors is not None:
                    return await _render_edit_validation_error(
                        self.form_renderer, request, resource, item_id, data, errors
                    )
                logger.exception("admin.update_failed")
                return HTMLResponse("Unable to update record", status_code=503)
            if updated_record is None:
                return HTMLResponse("Not found", status_code=404)
            try:
                await _maybe_await(resource.after_update(updated_record))
            except Exception:  # noqa: BLE001 — record is already persisted
                logger.exception("admin.after_update_failed")
                return HTMLResponse(
                    "Record updated, but finalization failed", status_code=500
                )

            from starlette.responses import RedirectResponse

            url = admin_url(
                admin_prefix_from_request(request),
                resource.name or "",
                f"{item_id}",
            )
            if request.headers.get("HX-Request") == "true":
                response = HTMLResponse("")
                response.headers["HX-Redirect"] = url
                response.headers["HX-Trigger"] = (
                    '{"show-toast":{"message":"Updated successfully","type":"success"}}'
                )
                return response
            return RedirectResponse(url=url, status_code=302)

        if request.method == "POST":
            return HTMLResponse("Resource data source unavailable", status_code=503)
        return await self.form_renderer.render_edit(
            request,
            resource,
            item_id,
            user=getattr(getattr(request, "state", None), "user", None),
        )


class InlineMutationActionHandler:
    """Render and persist the resource's two inline-edit contracts.

    ``field`` serves the field renderer's ``GET`` editor and ``POST`` submit.
    ``inline`` serves the detail renderer's ``GET`` page and ``PATCH`` submit.
    Both paths share record lookup, schema allow-listing, coercion, permission
    hooks, and lifecycle callbacks so an inline control cannot bypass CRUD
    policy or mass-assignment protection.
    """

    def __init__(self, config: AdminConfig, resource_name: str) -> None:
        self._config = config
        self.resource_name = resource_name

    def can_handle(self, action: str) -> bool:
        return action in {"field", "inline", "inline-edit"}

    @staticmethod
    def _as_dict(record: Any) -> dict[str, Any]:
        if isinstance(record, dict):
            return dict(record)
        if hasattr(record, "model_dump"):
            return dict(record.model_dump())
        if hasattr(record, "__dict__"):
            return dict(vars(record))
        return {}

    @staticmethod
    def _field_schema(resource: Any, field_name: str) -> Any | None:
        # Explicit declarative fields are the resource's canonical form/view
        # contract, even when a backing model is also present. Falling back to
        # generated model fields here would bypass visibility and readonly
        # metadata on inline routes. A malformed extension must not turn an
        # inline request into a traceback-bearing response.
        try:
            declared_fields = getattr(resource, "fields", ()) or ()
            field = next(
                (
                    field
                    for field in declared_fields
                    if getattr(field, "name", None) == field_name
                ),
                None,
            )
            if field is not None:
                return field

            model = getattr(resource, "model", None)
            if model is not None:
                from lexigram.admin.forms.components import FormSchemaGenerator

                schema = FormSchemaGenerator().from_pydantic(model)
                return next(
                    (field for field in schema.fields if field.name == field_name),
                    None,
                )
        except Exception:  # noqa: BLE001 — malformed schema is not a server error
            logger.exception("admin.inline_field_schema_failed", field=field_name)
            return None

        # Resources using only the declarative SchemaField system may not bind
        # a Pydantic/dataclass model; an absent declaration is never editable.
        return None

    async def _load_record(self, resource: Any, item_id: str) -> tuple[Any, Any]:
        data_source = get_resource_data_source(resource)
        if data_source is None or not hasattr(data_source, "find_one"):
            return None, None
        return data_source, await data_source.find_one(item_id)

    @staticmethod
    def _inline_field_editable(resource: Any, field_name: str, field_schema: Any) -> bool:
        """Return whether a field is allowed in the inline-write contract."""
        protected = set(
            getattr(resource, "protected_form_fields", PROTECTED_FORM_FIELDS)
            or PROTECTED_FORM_FIELDS
        )
        protected.update(getattr(resource, "form_exclude_fields", ()) or ())
        protected.update(getattr(resource, "readonly_fields", ()) or ())
        return bool(
            field_name not in protected
            and getattr(field_schema, "visible_in_form", True)
            and getattr(field_schema, "visible_in_view", True)
            and not getattr(field_schema, "readonly", False)
        )

    async def _authorize_update(self, resource: Any, record: Any) -> bool:
        hook = getattr(resource, "can_update", None)
        if not callable(hook):
            return True
        return await _call_permission_hook(hook, record)

    async def _coerce_field_value(
        self,
        resource: Any,
        field_name: str,
        form: Any,
    ) -> tuple[Any | None, str | None]:
        """Coerce one submitted field and return a user-facing error."""
        try:
            values = form.getlist(field_name) if hasattr(form, "getlist") else []
            # Some form adapters return None or a scalar from getlist despite
            # the Starlette MultiDict contract. Normalize those values before
            # applying checkbox/multi-value semantics.
            if values is None:
                values = []
            elif isinstance(values, (str, bytes)):
                values = [values]
            else:
                values = list(values)
            raw_value: Any
            if len(values) > 1:
                raw_value = values
            elif values:
                raw_value = values[0]
            else:
                raw_value = form.get(field_name)
        except (AttributeError, KeyError, TypeError, ValueError):
            return None, "Invalid form data"

        field_schema = self._field_schema(resource, field_name)
        if field_schema is None:
            return None, "Field not found"
        if not self._inline_field_editable(resource, field_name, field_schema):
            return None, "This field is read-only"

        # A checkbox has no successful control when it is switched off.
        if raw_value is None and field_schema.__class__.__name__ == "BooleanField":
            raw_value = ""

        from lexigram.admin.resources.form_guard import sanitize_form_data

        model = getattr(resource, "model", None)
        try:
            cleaned = sanitize_form_data(
                {field_name: raw_value},
                model=model,
                protected_fields=getattr(resource, "protected_form_fields", ()),
                allow_extra_fields=False,
            )
        except (TypeError, ValueError):
            return None, "Invalid value"
        except Exception:  # noqa: BLE001 — custom coercers must fail safely
            logger.exception("admin.inline_field_coercion_failed", field=field_name)
            return None, "Unable to validate field"
        if field_name not in cleaned:
            return None, "This field cannot be updated"

        value = cleaned[field_name]
        if model is not None:
            try:
                hints = get_type_hints(model)
                expected = hints.get(field_name)
                if expected is not None:
                    from pydantic import TypeAdapter

                    value = TypeAdapter(expected).validate_python(value)
            except ImportError:
                pass
            except (NameError, TypeError, ValueError):
                return None, "Invalid value"
            except Exception:  # noqa: BLE001 — a malformed model must not leak
                logger.exception("admin.inline_field_validation_failed", field=field_name)
                return None, "Unable to validate field"
        else:
            # Untyped declarative resources still have field-level coercion and
            # validators. Do not persist the browser's raw string when a
            # SchemaField can produce the declared Python value.
            try:
                result = field_schema.from_form(raw_value)
                if result.is_err():
                    return None, str(result.unwrap_err())
                value = result.unwrap()
                if field_schema.required and (
                    value is None or (isinstance(value, str) and not value.strip())
                ):
                    return None, "This field is required"
                validated = field_schema.validate_value(value)
                if validated.is_err():
                    return None, str(validated.unwrap_err())
                value = validated.unwrap()
            except (AttributeError, TypeError, ValueError):
                return None, "Invalid value"
            except Exception:  # noqa: BLE001 — custom field validators are untrusted
                logger.exception("admin.inline_field_validation_failed", field=field_name)
                return None, "Unable to validate field"
        return value, None

    async def _update_field(
        self,
        request: StarletteRequest,
        resource: Any,
        item_id: str,
        field_name: str,
        form: Any,
    ) -> tuple[Any, str | None]:
        try:
            data_source, record = await self._load_record(resource, item_id)
        except Exception as exc:  # noqa: BLE001 — storage failures are recoverable UI errors
            logger.exception("admin.inline_lookup_failed", error=str(exc))
            return None, "Unable to load record"
        if data_source is None:
            return None, "Inline editing is not available"
        if record is None:
            return None, "Not found"
        try:
            if not await self._authorize_update(resource, record):
                return None, "This record cannot be updated"
        except (PermissionError, PermissionDeniedError):
            return None, "Forbidden"
        except Exception:  # noqa: BLE001 — authorization extensions fail closed
            logger.exception("admin.inline_authorization_failed")
            return None, "Forbidden"
        if not await _field_view_allowed(request, resource, field_name):
            return None, "Forbidden"
        if await _field_masked(request, resource, field_name):
            return None, "Forbidden"
        if not await _field_edit_allowed(request, resource, field_name):
            return None, "Forbidden"

        value, error = await self._coerce_field_value(resource, field_name, form)
        if error:
            return None, error

        try:
            requested_change = {field_name: value}
            before_update = getattr(resource, "before_update", None)
            changed = (
                await _maybe_await(before_update(item_id, requested_change))
                if callable(before_update)
                else requested_change
            )
            if changed is None:
                changed = requested_change
            if not isinstance(changed, Mapping):
                logger.error("admin.inline_before_update_invalid_result", field=field_name)
                return None, "Unable to update record"
            # Hooks are trusted server code, but keep inline updates scoped to
            # the requested field to preserve the endpoint's narrow contract.
            changed = {field_name: changed.get(field_name, value)}
            updated = await _maybe_await(data_source.update(item_id, changed))
        except (PermissionError, PermissionDeniedError):
            return None, "Forbidden"
        except LookupError:
            return None, "Not found"
        except (TypeError, ValueError):
            return None, "Invalid value"
        except NotImplementedError:
            return None, "Inline editing is not available"
        except Exception:  # noqa: BLE001 — hook/storage failures are sanitized
            logger.exception("admin.inline_update_failed")
            return None, "Unable to update record"
        if updated is None:
            return None, "Not found"
        after_update = getattr(resource, "after_update", None)
        if callable(after_update):
            try:
                await _maybe_await(after_update(updated))
            except Exception:  # noqa: BLE001 — the write already succeeded
                logger.exception("admin.inline_after_update_failed")
                return None, "Record updated, but finalization failed"
        return updated, None

    def _render_display_cell(
        self,
        item_id: str,
        field_name: str,
        value: Any,
        request: StarletteRequest | None = None,
    ) -> str:
        from html import escape

        safe_id = escape(str(item_id), quote=True)
        safe_field = escape(field_name, quote=True)
        display = escape(str(value if value is not None else ""))
        prefix = admin_prefix_from_request(request) if request is not None else self._config.prefix
        url = f"{prefix.rstrip('/')}/{self.resource_name}/{safe_id}/field/{safe_field}"
        return (
            '<td class="py-2 text-sm text-foreground">'
            f'<span class="inline-edit-value">{display}</span>'
            f'<button type="button" class="ml-2 text-xs text-primary-600 '
            f'hover:text-primary-800" aria-label="Edit {safe_field}" '
            f'hx-get="{url}" hx-target="closest td" hx-swap="outerHTML">'
            "Edit</button></td>"
        )

    async def handle(
        self, request: StarletteRequest, resource: Any, **kwargs: Any
    ) -> HTMLResponse:
        item_id = str(request.path_params.get("id", ""))
        if resource is None or not item_id:
            return HTMLResponse("Not found", status_code=404)

        if request.method == "GET":
            if self.can_handle(request.scope.get("admin_action", "")) and request.scope.get(
                "admin_action"
            ) in {"inline", "inline-edit"}:
                from lexigram.admin.engine.renderer import AdminRenderer
                from lexigram.admin.resources.detail_renderer import DetailRenderer

                try:
                    data_source, record = await self._load_record(resource, item_id)
                except Exception:  # noqa: BLE001 — storage failures are sanitized
                    logger.exception("admin.inline_detail_lookup_failed")
                    return HTMLResponse("Unable to load record", status_code=503)
                if data_source is None or record is None:
                    return HTMLResponse("Not found", status_code=404)
                try:
                    return await DetailRenderer(
                        self._config,
                        self.resource_name,
                        AdminRenderer(None),
                    ).render_inline_edit(
                        request,
                        resource,
                        item_id,
                        user=getattr(getattr(request, "state", None), "user", None),
                    )
                except Exception:  # noqa: BLE001 — rendering/storage failures are sanitized
                    logger.exception("admin.inline_detail_render_failed")
                    return HTMLResponse("Unable to render record", status_code=500)

            field_name = str(request.path_params.get("field", ""))
            if not field_name:
                return HTMLResponse("Field not found", status_code=404)
            field_schema = self._field_schema(resource, field_name)
            if field_schema is None:
                return HTMLResponse("Field not found", status_code=404)
            if not self._inline_field_editable(resource, field_name, field_schema):
                return HTMLResponse("This field is read-only", status_code=403)
            if not await _field_view_allowed(request, resource, field_name):
                return HTMLResponse("Forbidden", status_code=403)
            if await _field_masked(request, resource, field_name):
                return HTMLResponse("Forbidden", status_code=403)
            if not await _field_edit_allowed(request, resource, field_name):
                return HTMLResponse("Forbidden", status_code=403)
            try:
                data_source, record = await self._load_record(resource, item_id)
            except Exception:  # noqa: BLE001 — storage failures are sanitized
                logger.exception("admin.inline_field_lookup_failed")
                return HTMLResponse("Unable to load record", status_code=503)
            if data_source is None or record is None:
                return HTMLResponse("Not found", status_code=404)
            try:
                if not await self._authorize_update(resource, record):
                    return HTMLResponse("Forbidden", status_code=403)
            except (PermissionError, PermissionDeniedError):
                return HTMLResponse("Forbidden", status_code=403)
            except Exception:  # noqa: BLE001 — authorization extensions fail closed
                logger.exception("admin.inline_authorization_failed")
                return HTMLResponse("Forbidden", status_code=403)

            from lexigram.admin.resources.field_renderer import FieldRenderer

            try:
                editor = await FieldRenderer(
                    self._config,
                    self.resource_name,
                ).render_field(
                    request,
                    resource,
                    field_name,
                    item_id=item_id,
                    user=getattr(getattr(request, "state", None), "user", None),
                )
            except Exception:  # noqa: BLE001 — renderer extensions are sanitized
                logger.exception("admin.inline_field_render_failed", field=field_name)
                return HTMLResponse("Unable to render field", status_code=500)
            from html import escape

            return HTMLResponse(
                '<td class="py-2 text-sm text-foreground">'
                + editor.body.decode("utf-8")
                + f'<button type="button" class="ml-2 text-xs text-muted-foreground" '
                f'hx-get="{escape(request.url.path, quote=True)}" '
                f'hx-target="closest td" hx-swap="outerHTML">Cancel</button></td>',
                status_code=editor.status_code,
            )

        try:
            form = (
                request.scope["admin_form_data"]
                if "admin_form_data" in request.scope
                else await request.form()
            )
        except Exception:  # noqa: BLE001 — malformed request bodies are sanitized
            logger.exception("admin.inline_form_parse_failed")
            return HTMLResponse("Invalid form data", status_code=400)
        if request.scope.get("admin_action") == "field":
            field_name = str(request.path_params.get("field", ""))
        else:
            field_name = str(request.query_params.get("field", ""))
        if not field_name:
            return HTMLResponse("Missing field", status_code=400)

        updated, error = await self._update_field(
            request,
            resource,
            item_id,
            field_name,
            form,
        )
        if error:
            if error == "Not found":
                status = 404
            elif error in {"This field is read-only", "This record cannot be updated"} or error == "Forbidden":
                status = 403
            elif error == "Inline editing is not available" or error == "Unable to load record":
                status = 503
            else:
                status = 422
            return HTMLResponse(error, status_code=status)

        item_dict = self._as_dict(updated)
        if request.scope.get("admin_action") == "field":
            return HTMLResponse(
                self._render_display_cell(
                    item_id,
                    field_name,
                    item_dict.get(field_name),
                    request=request,
                )
            )

        from html import escape

        return HTMLResponse(
            "<tr>"
            f'<td class="py-2 pr-4 align-top text-sm font-medium text-muted-foreground">'
            f"<strong>{escape(field_name)}</strong></td>"
            + self._render_display_cell(
                item_id,
                field_name,
                item_dict.get(field_name),
                request=request,
            )
            + "</tr>"
        )


class CloneActionHandler:
    """Handler for the ``clone`` action — duplicates a record and redirects."""

    def can_handle(self, action: str) -> bool:
        return action == "clone"

    async def handle(
        self, request: StarletteRequest, resource: Any, **kwargs: Any
    ) -> Any:
        from lexigram.admin.resources.base import Resource

        item_id = request.path_params.get("id", "?")

        if not isinstance(resource, Resource):
            return HTMLResponse(
                "<h1>Clone not supported for this resource</h1>", status_code=400
            )

        try:
            new_record = await resource.duplicate(item_id)
        except LookupError:
            return HTMLResponse("Not found", status_code=404)
        except (PermissionError, PermissionDeniedError):
            return HTMLResponse("Forbidden", status_code=403)
        except (NotImplementedError, RuntimeError) as exc:
            logger.exception("admin.clone_unavailable", error=str(exc))
            return HTMLResponse("Clone is unavailable", status_code=503)
        except (TypeError, ValueError) as exc:
            # A before_clone hook may reject source data. Do not expose a
            # traceback or persist a partial result, but make the client able
            # to distinguish invalid clone input from a missing resource.
            logger.info("admin.clone_validation_failed", error=str(exc))
            return HTMLResponse("Clone validation failed", status_code=422)
        except Exception:  # noqa: BLE001 — hook/storage failures are sanitized
            logger.exception("admin.clone_failed")
            return HTMLResponse("Unable to clone record", status_code=500)
        raw_new_id = (
            new_record.get("id")
            if isinstance(new_record, dict)
            else getattr(new_record, "id", None)
        )
        if raw_new_id is None:
            logger.error("admin.clone_missing_created_id")
            return HTMLResponse("Unable to clone record", status_code=500)
        new_id = str(raw_new_id)

        url = admin_url(
            admin_prefix_from_request(request),
            resource.name or "",
            f"{new_id}/edit",
        )
        return _mutation_redirect(request, url, "Record cloned successfully")


class RestoreActionHandler:
    """Handler for the ``restore`` action — restores a soft-deleted record and redirects."""

    def can_handle(self, action: str) -> bool:
        return action == "restore"

    async def handle(
        self, request: StarletteRequest, resource: Any, **kwargs: Any
    ) -> Any:
        from lexigram.admin.resources.base import Resource

        item_id = request.path_params.get("id", "?")

        if not isinstance(resource, Resource):
            return HTMLResponse(
                "<h1>Restore not supported for this resource</h1>", status_code=400
            )

        data_source = get_resource_data_source(resource)
        if data_source is None or not callable(getattr(data_source, "find_one", None)):
            return HTMLResponse("Restore is unavailable", status_code=503)
        try:
            item = await data_source.find_one(item_id)
        except Exception as exc:  # noqa: BLE001 — storage details stay private
            logger.exception("admin.restore_lookup_failed", error=str(exc))
            return HTMLResponse("Unable to load record", status_code=503)
        can_update = getattr(resource, "can_update", None)
        if item is None:
            return HTMLResponse("Not found", status_code=404)
        if can_update and not await _call_permission_hook(can_update, item):
            return HTMLResponse("This record cannot be restored", status_code=403)

        try:
            restored = await resource.restore(item_id)
        except LookupError:
            return HTMLResponse("Not found", status_code=404)
        except (PermissionError, PermissionDeniedError):
            return HTMLResponse("Forbidden", status_code=403)
        except (NotImplementedError, RuntimeError) as exc:
            logger.exception("admin.restore_unavailable", error=str(exc))
            return HTMLResponse("Restore is unavailable", status_code=503)
        except (TypeError, ValueError) as exc:
            logger.info("admin.restore_validation_failed", error=str(exc))
            return HTMLResponse("Restore validation failed", status_code=422)
        except Exception:  # noqa: BLE001 — hook/storage failures are sanitized
            logger.exception("admin.restore_failed")
            return HTMLResponse("Unable to restore record", status_code=500)
        if restored is None:
            return HTMLResponse("Not found", status_code=404)
        raw_new_id = (
            restored.get("id")
            if isinstance(restored, dict)
            else getattr(restored, "id", item_id)
        )
        new_id = str(raw_new_id if raw_new_id is not None else item_id)

        url = admin_url(
            admin_prefix_from_request(request),
            resource.name or "",
            f"{new_id}/edit",
        )
        return _mutation_redirect(request, url, "Record restored successfully")


class PurgeActionHandler:
    """Handler for the ``purge`` action — permanently deletes a record and redirects."""

    def can_handle(self, action: str) -> bool:
        return action == "purge"

    async def handle(
        self, request: StarletteRequest, resource: Any, **kwargs: Any
    ) -> Any:
        from lexigram.admin.resources.base import Resource

        item_id = request.path_params.get("id", "?")

        if not isinstance(resource, Resource):
            return HTMLResponse(
                "<h1>Purge not supported for this resource</h1>", status_code=400
            )

        data_source = get_resource_data_source(resource)
        if data_source is None or not callable(getattr(data_source, "find_one", None)):
            return HTMLResponse("Purge is unavailable", status_code=503)
        try:
            item = await data_source.find_one(item_id)
        except Exception as exc:  # noqa: BLE001 — storage details stay private
            logger.exception("admin.purge_lookup_failed", error=str(exc))
            return HTMLResponse("Unable to load record", status_code=503)
        can_delete = getattr(resource, "can_delete", None)
        if item is None:
            return HTMLResponse("Not found", status_code=404)
        if can_delete and not await _call_permission_hook(can_delete, item):
            return HTMLResponse("This record cannot be deleted", status_code=403)

        try:
            await resource.purge(item_id)
        except LookupError:
            return HTMLResponse("Not found", status_code=404)
        except (PermissionError, PermissionDeniedError):
            return HTMLResponse("Forbidden", status_code=403)
        except (NotImplementedError, RuntimeError) as exc:
            logger.exception("admin.purge_unavailable", error=str(exc))
            return HTMLResponse("Purge is unavailable", status_code=503)
        except (TypeError, ValueError) as exc:
            logger.info("admin.purge_validation_failed", error=str(exc))
            return HTMLResponse("Purge validation failed", status_code=422)
        except Exception:  # noqa: BLE001 — hook/storage failures are sanitized
            logger.exception("admin.purge_failed")
            return HTMLResponse("Unable to purge record", status_code=500)

        url = admin_url(
            admin_prefix_from_request(request),
            resource.name or "",
        )
        return _mutation_redirect(request, url, "Record permanently deleted")


_MAX_RELATION_OPTIONS = 200
_MAX_RELATION_OPTION_TEXT = 500


class RelationOptionsActionHandler:
    """Serve ``<option>`` markup for searchable relation selects.

    Registered as ``relation-options``; the route lives on the *related*
    resource (``/{prefix}/{resource}/relation-options``) and is resolved
    against the mounted resource register, so the response is generated from
    the same data-source instance the related resource uses at runtime.
    """

    def __init__(self, resources: dict[str, Any] | None = None) -> None:
        self._resources = resources or {}

    def can_handle(self, action: str) -> bool:
        return action == "relation-options"

    @staticmethod
    def _request_permission_service(request: StarletteRequest) -> Any | None:
        """Resolve the mounted field-permission service without MagicMock fallbacks."""
        try:
            app = request.app
        except (AttributeError, KeyError, RuntimeError):
            app = None
        service = getattr(getattr(app, "state", None), "permission_service", None)
        if service is not None and callable(getattr(service, "can_view_field", None)):
            return service
        try:
            state = request.state
        except (AttributeError, KeyError, RuntimeError):
            state = None
        storage = getattr(state, "_state", None)
        if isinstance(storage, dict):
            service = storage.get("permission_service")
        elif isinstance(state, dict):
            service = state.get("permission_service")
        else:
            try:
                service = vars(state).get("permission_service")
            except TypeError:
                service = None
        return (
            service
            if service is not None and callable(getattr(service, "can_view_field", None))
            else None
        )

    async def _authorize_source_field(self, request: StarletteRequest) -> bool:
        """Enforce the parent form field policy for searchable options."""
        source = (request.query_params.get("source") or "").strip()
        field = (request.query_params.get("field") or "").strip()
        if not source or not field:
            # Keep compatibility with callers that use this endpoint as a
            # generic related-resource lookup; the mounted resource-level
            # permission check remains authoritative in ResourceHandler.
            return True
        service = self._request_permission_service(request)
        if service is None:
            return True
        user = getattr(getattr(request, "state", None), "user", None)
        if user is None:
            return False
        try:
            allowed = service.can_view_field(user, source, field)
            return bool(await allowed) if inspect.isawaitable(allowed) else bool(allowed)
        except Exception:  # noqa: BLE001 — lookup authorization fails closed
            logger.exception(
                "admin.relation_options_permission_check_failed",
                resource=source,
                field=field,
            )
            return False

    async def handle(
        self, request: StarletteRequest, resource: Any, **kwargs: Any
    ) -> HTMLResponse:
        from html import escape

        if resource is None:
            return HTMLResponse("", status_code=404)
        if not await self._authorize_source_field(request):
            return HTMLResponse("Forbidden", status_code=403)

        ds = get_resource_data_source(resource)
        if ds is None or not hasattr(ds, "find_many"):
            return HTMLResponse("", status_code=200)

        from lexigram.admin.data.query import QuerySpec

        try:
            result = await ds.find_many(QuerySpec(per_page=200, sort_by="id"))
        except Exception as exc:  # noqa: BLE001 — relation lookups are optional form enhancements
            logger.exception(
                "admin.relation_options_lookup_failed",
                resource=getattr(resource, "name", None),
                error=str(exc),
            )
            return HTMLResponse("", status_code=503)
        if hasattr(result, "items"):
            raw_records = result.items
        elif isinstance(result, list):
            raw_records = result
        else:
            raw_records = []
        try:
            records = list(raw_records)[:_MAX_RELATION_OPTIONS]
        except (TypeError, ValueError):
            records = []

        needle = (
            (request.query_params.get("q") or "")[:_MAX_RELATION_OPTION_TEXT]
            .strip()
            .lower()
        )
        options: list[str] = []
        for record in records:
            try:
                if isinstance(record, dict):
                    record_id = record.get("id", record.get("pk"))
                    label = (
                        record.get("name")
                        or record.get("title")
                        or record.get("label")
                        or record.get("email")
                    )
                    if label is None or not str(label).strip():
                        label = record_id
                else:
                    record_id = getattr(record, "id", getattr(record, "pk", None))
                    label = (
                        getattr(record, "name", None)
                        or getattr(record, "title", None)
                        or getattr(record, "label", None)
                        or getattr(record, "email", None)
                    )
                    if label is None or not str(label).strip():
                        # Domain records often expose their display name only via
                        # __str__. Use that before falling back to the primary key.
                        label = str(record)
                        if not label.strip() or label == repr(record):
                            label = record_id
                if record_id is None:
                    continue
                value = str(record_id)[:_MAX_RELATION_OPTION_TEXT]
                label = str(label if label is not None else value)[
                    :_MAX_RELATION_OPTION_TEXT
                ]
                if needle and needle not in label.lower():
                    continue
                options.append(
                    f'<option value="{escape(value)}">{escape(label)}</option>'
                )
            except (AttributeError, TypeError, ValueError):
                # One malformed record must not break the entire select.
                continue
        return HTMLResponse("".join(options))


class ImportActionHandler:
    """Handler for import download routes (example CSV, failed-import report).

    Serves GET ``import-example`` (the resource's declared
    :class:`~lexigram.admin.actions.standard.ImportAction` template) and
    GET ``import-report`` (a stored failed-import report as CSV).
    """

    _ACTIONS = ("import-example", "import-report")

    def can_handle(self, action: str) -> bool:
        """Whether this handler serves the given route action."""
        return action in self._ACTIONS

    @staticmethod
    def _find_import_action(resource: Any) -> Any:
        """Locate the resource's declared ImportAction, if any."""
        from lexigram.admin.actions.standard import ImportAction

        for collection in ("header_actions", "actions"):
            for action in getattr(resource, collection, None) or []:
                if isinstance(action, ImportAction):
                    return action
        return None

    @staticmethod
    def _csv_response(content: str, filename: str) -> Any:
        """Build an attachment CSV response."""
        from starlette.responses import Response

        return Response(
            content=content,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    async def handle(
        self, request: StarletteRequest, resource: Any, **kwargs: Any
    ) -> Any:
        from starlette.responses import HTMLResponse

        action = self._find_import_action(resource)
        if action is None:
            return HTMLResponse(
                "<h1>Import not configured for this resource</h1>",
                status_code=404,
            )
        if request.method != "GET":
            return HTMLResponse("Method not allowed", status_code=405)

        requested = request.scope.get("admin_action", "")
        if requested == "import-example":
            content = action.example_csv()
            if not content:
                return HTMLResponse(
                    "<h1>No example CSV configured</h1>", status_code=404
                )
            return self._csv_response(content, action.example_filename)

        report_id = request.query_params.get("report_id", "")
        content = action.report_csv(report_id)
        if content is None:
            return HTMLResponse("<h1>Report not found</h1>", status_code=404)
        filename = action.report_filename(report_id) or "import-errors.csv"
        return self._csv_response(content, filename)


class DeleteActionHandler:
    """Handler for delete-confirm and delete actions."""

    def can_handle(self, action: str) -> bool:
        return action in ("delete-confirm", "delete")

    async def handle(
        self, request: StarletteRequest, resource: Any, **kwargs: Any
    ) -> Any:
        item_id = request.path_params.get("id", "?")

        if request.method == "GET":
            return await self._confirm_delete(request, resource, item_id)
        return await self._execute_delete(request, resource, item_id)

    async def _confirm_delete(
        self, request: StarletteRequest, resource: Any, item_id: str
    ) -> Any:
        from lexigram.admin.resources.base import Resource as AdminResource

        label = getattr(resource, "label", "Record")
        record_label = f"{label} #{item_id}"

        data_source = get_resource_data_source(resource)
        if isinstance(resource, AdminResource) and data_source is not None:
            try:
                item = await data_source.find_one(item_id)
                if item:
                    for field in ("name", "title", "email", "username", "label"):
                        val = (
                            item.get(field)
                            if isinstance(item, dict)
                            else getattr(item, field, None)
                        )
                        if val:
                            record_label = str(val)
                            break
            except Exception:  # noqa: S110 — intentional best-effort fallback
                pass

        delete_url = admin_url(
            admin_prefix_from_request(request),
            resource.name or "",
            f"{item_id}/delete",
        )

        from lexigram.admin.ui.organisms.admin_slide_over import render_delete_confirm

        html = render_delete_confirm(
            record_label=record_label,
            delete_url=delete_url,
        )
        return HTMLResponse(html)

    async def _execute_delete(
        self, request: StarletteRequest, resource: Any, item_id: str
    ) -> Any:
        from lexigram.admin.resources.base import Resource as AdminResource

        data_source = get_resource_data_source(resource)
        if isinstance(resource, AdminResource) and data_source is not None:
            try:
                item = await data_source.find_one(item_id)
            except Exception as exc:  # noqa: BLE001 — storage details stay private
                logger.exception("admin.delete_lookup_failed", error=str(exc))
                return HTMLResponse("Unable to load record", status_code=503)
            if item is None:
                return HTMLResponse("Not found", status_code=404)

            can_delete = getattr(resource, "can_delete", None)
            if can_delete and not await _call_permission_hook(can_delete, item):
                is_htmx = request.headers.get("HX-Request") == "true"
                if is_htmx:
                    response = HTMLResponse("")
                    response.headers["HX-Trigger"] = (
                        '{"show-toast":{"message":"This record cannot be deleted","type":"error"}}'
                    )
                    return response
                return HTMLResponse(
                    "<body>This record cannot be deleted</body>",
                    status_code=409,
                )

            before_delete = getattr(resource, "before_delete", None)
            if callable(before_delete):
                try:
                    await _maybe_await(before_delete(item_id))
                except (PermissionError, PermissionDeniedError):
                    return HTMLResponse("Forbidden", status_code=403)
                except LookupError:
                    return HTMLResponse("Not found", status_code=404)
                except (TypeError, ValueError) as exc:
                    logger.info("admin.delete_validation_failed", error=str(exc))
                    return HTMLResponse("Delete validation failed", status_code=422)
                except Exception:  # noqa: BLE001 — hook failures are sanitized
                    logger.exception("admin.before_delete_failed")
                    return HTMLResponse("Unable to delete record", status_code=500)

            # Resource declarations can opt into soft deletion. Keep the
            # legacy hard-delete default, but make the routed delete action
            # honor the same setting as ResourceController.delete().
            soft_delete = bool(getattr(resource, "soft_delete_enabled", False))
            try:
                if soft_delete:
                    from datetime import UTC, datetime

                    deleted = await data_source.update(
                        item_id, {"deleted_at": datetime.now(UTC).isoformat()}
                    )
                    success = deleted is not None
                else:
                    success = await data_source.delete(item_id)
            except NotImplementedError:
                return HTMLResponse("Delete is unavailable", status_code=503)
            except Exception as exc:  # noqa: BLE001 — storage details stay private
                logger.exception("admin.delete_failed", error=str(exc))
                return HTMLResponse("Unable to delete record", status_code=503)
            if not success:
                return HTMLResponse("Not found", status_code=404)

            after_delete = getattr(resource, "after_delete", None)
            if callable(after_delete):
                try:
                    await _maybe_await(after_delete(item_id))
                except Exception:  # noqa: BLE001 — record is already deleted
                    logger.exception("admin.after_delete_failed")
                    return HTMLResponse(
                        "Record deleted, but finalization failed", status_code=500
                    )

            is_htmx = request.headers.get("HX-Request") == "true"
            url = admin_url(
                admin_prefix_from_request(request),
                resource.name or "",
            )

            if is_htmx:
                response = HTMLResponse("")
                response.headers["HX-Trigger"] = (
                    '{"refresh-list":true,"show-toast":{"message":"Deleted successfully","type":"success"}}'
                )
                response.headers["HX-Redirect"] = url
                return response

            from starlette.responses import RedirectResponse

            return RedirectResponse(url=url, status_code=302)

        return HTMLResponse("Delete not supported", status_code=400)
