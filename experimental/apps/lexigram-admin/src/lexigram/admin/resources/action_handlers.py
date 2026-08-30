"""Record-level CRUD action handlers for Admin Resources.

List / detail / create / edit / clone / restore / purge / delete flows,
plus the form-data coercion helpers they share. Specialized handlers
(import, user permissions, bulk) live in :mod:`.handler`.
"""

from __future__ import annotations

from typing import Any, Protocol

from starlette.requests import Request as StarletteRequest
from starlette.responses import HTMLResponse

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
    "ListActionHandler",
    "PurgeActionHandler",
    "RelationOptionsActionHandler",
    "ResourceActionHandler",
    "RestoreActionHandler",
]

logger = get_logger(__name__)


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

            validated_data = validation.unwrap()
            validated = await resource.before_update(item_id, validated_data)
            record = await data_source.find_one(item_id)
            can_update = getattr(resource, "can_update", None)
            if can_update and not can_update(record):
                return HTMLResponse("This record cannot be updated", status_code=403)
            updated_record = await data_source.update(item_id, validated)
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

        new_record = await resource.duplicate(item_id)
        new_id = str(getattr(new_record, "id", "?"))
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
        if can_update and not can_update(item):
            return HTMLResponse("This record cannot be restored", status_code=403)

        restored = await resource.restore(item_id)
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
        if can_delete and not can_delete(item):
            return HTMLResponse("This record cannot be deleted", status_code=403)

        await resource.purge(item_id)
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
            if can_delete and not can_delete(item):
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

            success = await data_source.delete(item_id)
            if not success:
                return HTMLResponse("Not found", status_code=404)

            after_delete = getattr(resource, "after_delete", None)
            if after_delete:
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
