"""Record-level CRUD action handlers for Admin Resources.

List / detail / create / edit / clone / restore / purge / delete flows,
plus the form-data coercion helpers they share. Specialized handlers
(import, user permissions, bulk) live in :mod:`.handler`.
"""

from __future__ import annotations

import inspect
from typing import Any, Protocol, get_type_hints

from starlette.requests import Request as StarletteRequest
from starlette.responses import HTMLResponse

from lexigram.admin.config import AdminConfig
from lexigram.admin.resources.data_access import get_resource_data_source
from lexigram.admin.resources.form_coercion import (
    _validation_errors_to_dict,
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

        form = request.scope.get("admin_form_data") or await request.form()
        data = _form_data_dict(form)
        data.pop("csrf_token", None)

        data_source = get_resource_data_source(resource)
        if isinstance(resource, Resource) and data_source is not None:
            validation = await resource.before_validate(data)
            if validation.is_err():
                error = validation.unwrap_err()
                return await self.form_renderer.render_create(
                    request,
                    resource,
                    user=getattr(getattr(request, "state", None), "user", None),
                    errors=_validation_errors_to_dict(error),
                    data=data,
                )

            validated_data = validation.unwrap()
            validated = await resource.before_create(validated_data)
            record = await data_source.create(validated)
            if record is None:
                return HTMLResponse("Unable to create record", status_code=503)
            await resource.after_create(record)

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

        form = request.scope.get("admin_form_data") or await request.form()
        data = _form_data_dict(form)
        data.pop("csrf_token", None)

        data_source = get_resource_data_source(resource)
        if isinstance(resource, Resource) and data_source is not None:
            validation = await resource.before_validate(data)
            if validation.is_err():
                error = validation.unwrap_err()
                return await self.form_renderer.render_edit(
                    request,
                    resource,
                    item_id,
                    user=getattr(getattr(request, "state", None), "user", None),
                    errors=_validation_errors_to_dict(error),
                    data=data,
                )

            record = await data_source.find_one(item_id)
            if record is None:
                return HTMLResponse("Not found", status_code=404)
            can_update = getattr(resource, "can_update", None)
            if can_update and not await _call_permission_hook(can_update, record):
                return HTMLResponse("This record cannot be updated", status_code=403)
            validated_data = validation.unwrap()
            validated = await resource.before_update(item_id, validated_data)
            updated_record = await data_source.update(item_id, validated)
            if updated_record is None:
                return HTMLResponse("Not found", status_code=404)
            await resource.after_update(updated_record)

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
        model = getattr(resource, "model", None)
        if model is not None:
            from lexigram.admin.forms.components import FormSchemaGenerator

            schema = FormSchemaGenerator().from_pydantic(model)
            field = next(
                (field for field in schema.fields if field.name == field_name),
                None,
            )
            if field is not None:
                return field

        # Resources using the declarative SchemaField system may not bind a
        # Pydantic/dataclass model. Keep inline writes on the same allow-list
        # as their generated table/form configuration.
        return next(
            (
                field
                for field in getattr(resource, "fields", ()) or ()
                if getattr(field, "name", None) == field_name
            ),
            None,
        )

    async def _load_record(self, resource: Any, item_id: str) -> tuple[Any, Any]:
        data_source = get_resource_data_source(resource)
        if data_source is None or not hasattr(data_source, "find_one"):
            return None, None
        return data_source, await data_source.find_one(item_id)

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
        values = form.getlist(field_name) if hasattr(form, "getlist") else []
        raw_value: Any
        if len(values) > 1:
            raw_value = values
        elif values:
            raw_value = values[0]
        else:
            raw_value = form.get(field_name)

        field_schema = self._field_schema(resource, field_name)
        if field_schema is None:
            return None, "Field not found"
        if getattr(field_schema, "readonly", False):
            return None, "This field is read-only"

        # A checkbox has no successful control when it is switched off.
        if raw_value is None and field_schema.__class__.__name__ == "BooleanField":
            raw_value = ""

        from lexigram.admin.resources.form_guard import sanitize_form_data

        model = getattr(resource, "model", None)
        cleaned = sanitize_form_data(
            {field_name: raw_value},
            model=model,
            protected_fields=getattr(resource, "protected_form_fields", ()),
            allow_extra_fields=False,
        )
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
            except (NameError, TypeError, ValueError) as exc:
                return None, str(exc)
        else:
            # Untyped declarative resources still have field-level coercion and
            # validators. Do not persist the browser's raw string when a
            # SchemaField can produce the declared Python value.
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
        return value, None

    async def _update_field(
        self,
        request: StarletteRequest,
        resource: Any,
        item_id: str,
        field_name: str,
        form: Any,
    ) -> tuple[Any, str | None]:
        data_source, record = await self._load_record(resource, item_id)
        if data_source is None:
            return None, "Inline editing is not available"
        if record is None:
            return None, "Not found"
        if not await self._authorize_update(resource, record):
            return None, "This record cannot be updated"

        value, error = await self._coerce_field_value(resource, field_name, form)
        if error:
            return None, error

        try:
            changed = await resource.before_update(item_id, {field_name: value})
            changed = changed if isinstance(changed, dict) else {field_name: value}
            # Hooks are trusted server code, but keep inline updates scoped to
            # the requested field to preserve the endpoint's narrow contract.
            changed = {field_name: changed.get(field_name, value)}
            updated = await data_source.update(item_id, changed)
        except (LookupError, TypeError, ValueError) as exc:
            return None, str(exc)
        if updated is None:
            return None, "Not found"
        await resource.after_update(updated)
        return updated, None

    def _render_display_cell(
        self,
        item_id: str,
        field_name: str,
        value: Any,
    ) -> str:
        from html import escape

        safe_id = escape(str(item_id), quote=True)
        safe_field = escape(field_name, quote=True)
        display = escape(str(value if value is not None else ""))
        url = (
            f"{self._config.prefix.rstrip('/')}/{self.resource_name}/"
            f"{safe_id}/field/{safe_field}"
        )
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

                data_source, record = await self._load_record(resource, item_id)
                if data_source is None or record is None:
                    return HTMLResponse("Not found", status_code=404)
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

            field_name = str(request.path_params.get("field", ""))
            if not field_name:
                return HTMLResponse("Field not found", status_code=404)
            data_source, record = await self._load_record(resource, item_id)
            if data_source is None or record is None:
                return HTMLResponse("Not found", status_code=404)
            if not await self._authorize_update(resource, record):
                return HTMLResponse("Forbidden", status_code=403)

            from lexigram.admin.resources.field_renderer import FieldRenderer

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
            from html import escape

            return HTMLResponse(
                '<td class="py-2 text-sm text-foreground">'
                + editor.body.decode("utf-8")
                + f'<button type="button" class="ml-2 text-xs text-muted-foreground" '
                f'hx-get="{escape(request.url.path, quote=True)}" '
                f'hx-target="closest td" hx-swap="outerHTML">Cancel</button></td>',
                status_code=editor.status_code,
            )

        form = request.scope.get("admin_form_data") or await request.form()
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
            status = 404 if error == "Not found" else 403 if "cannot" in error else 422
            return HTMLResponse(error, status_code=status)

        item_dict = self._as_dict(updated)
        if request.scope.get("admin_action") == "field":
            return HTMLResponse(
                self._render_display_cell(item_id, field_name, item_dict.get(field_name))
            )

        from html import escape

        return HTMLResponse(
            "<tr>"
            f'<td class="py-2 pr-4 align-top text-sm font-medium text-muted-foreground">'
            f"<strong>{escape(field_name)}</strong></td>"
            + self._render_display_cell(item_id, field_name, item_dict.get(field_name))
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
        raw_new_id = (
            new_record.get("id")
            if isinstance(new_record, dict)
            else getattr(new_record, "id", None)
        )
        if raw_new_id is None:
            return HTMLResponse("Clone failed", status_code=500)
        new_id = str(raw_new_id)
        from starlette.responses import RedirectResponse

        url = admin_url(
            admin_prefix_from_request(request),
            resource.name or "",
            f"{new_id}/edit",
        )
        return RedirectResponse(url=url, status_code=302)


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
        item = await data_source.find_one(item_id) if data_source is not None else None
        can_update = getattr(resource, "can_update", None)
        if item is None:
            return HTMLResponse("Not found", status_code=404)
        if can_update and not await _call_permission_hook(can_update, item):
            return HTMLResponse("This record cannot be restored", status_code=403)

        try:
            restored = await resource.restore(item_id)
        except LookupError:
            return HTMLResponse("Not found", status_code=404)
        if restored is None:
            return HTMLResponse("Not found", status_code=404)
        new_id = str(getattr(restored, "id", item_id))
        from starlette.responses import RedirectResponse

        url = admin_url(
            admin_prefix_from_request(request),
            resource.name or "",
            f"{new_id}/edit",
        )
        return RedirectResponse(url=url, status_code=302)


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
        item = await data_source.find_one(item_id) if data_source is not None else None
        can_delete = getattr(resource, "can_delete", None)
        if item is None:
            return HTMLResponse("Not found", status_code=404)
        if can_delete and not await _call_permission_hook(can_delete, item):
            return HTMLResponse("This record cannot be deleted", status_code=403)

        try:
            await resource.purge(item_id)
        except LookupError:
            return HTMLResponse("Not found", status_code=404)
        from starlette.responses import RedirectResponse

        url = admin_url(
            admin_prefix_from_request(request),
            resource.name or "",
        )
        return RedirectResponse(url=url, status_code=302)


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

    async def handle(
        self, request: StarletteRequest, resource: Any, **kwargs: Any
    ) -> HTMLResponse:
        from html import escape

        if resource is None:
            return HTMLResponse("", status_code=404)

        ds = get_resource_data_source(resource)
        if ds is None or not hasattr(ds, "find_many"):
            return HTMLResponse("", status_code=200)

        from lexigram.admin.data.query import QuerySpec

        result = await ds.find_many(QuerySpec(per_page=200, sort_by="id"))
        if hasattr(result, "items"):
            records = result.items
        elif isinstance(result, list):
            records = result
        else:
            records = []

        needle = (request.query_params.get("q") or "").strip().lower()
        options: list[str] = []
        for record in records:
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
                    # __str__. Use that before falling back to the primary key;
                    # this also keeps searchable labels consistent with table
                    # and select renderers.
                    label = str(record)
                    if not label.strip() or label == repr(record):
                        label = record_id
            if record_id is None:
                continue
            value = str(record_id)
            label = str(label if label is not None else value)
            if needle and needle not in label.lower():
                continue
            options.append(
                f'<option value="{escape(value)}">{escape(label)}</option>'
            )
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
            item = await data_source.find_one(item_id)
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
                await before_delete(item_id)

            # Resource declarations can opt into soft deletion. Keep the
            # legacy hard-delete default, but make the routed delete action
            # honor the same setting as ResourceController.delete().
            soft_delete = bool(getattr(resource, "soft_delete_enabled", False))
            if soft_delete:
                from datetime import UTC, datetime

                deleted = await data_source.update(
                    item_id, {"deleted_at": datetime.now(UTC).isoformat()}
                )
                success = deleted is not None
            else:
                success = await data_source.delete(item_id)
            if not success:
                return HTMLResponse("Not found", status_code=404)

            after_delete = getattr(resource, "after_delete", None)
            if callable(after_delete):
                await after_delete(item_id)

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

            return HTMLResponse(
                f'<html><head><meta http-equiv="refresh" content="0;url={url}"></head><body></body></html>'
            )

        return HTMLResponse("Delete not supported", status_code=400)
