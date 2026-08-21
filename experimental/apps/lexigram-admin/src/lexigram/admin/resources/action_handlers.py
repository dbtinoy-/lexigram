"""Record-level CRUD action handlers for Admin Resources.

List / detail / create / edit / clone / restore / purge / delete flows,
plus the form-data coercion helpers they share. Specialized handlers
(import, user permissions, bulk) live in :mod:`.handler`.
"""

from __future__ import annotations

from typing import Any, Protocol

from starlette.requests import Request as StarletteRequest
from starlette.responses import HTMLResponse

from lexigram.admin.resources.form_coercion import (
    _validation_errors_to_dict,
)
from lexigram.logging import get_logger

logger = get_logger(__name__)


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
        return await self.detail_renderer.render_detail(request, resource, item_id)


class CreateActionHandler:
    def __init__(self, form_renderer: Any):
        self.form_renderer = form_renderer

    def can_handle(self, action: str) -> bool:
        return action == "create"

    async def handle(
        self, request: StarletteRequest, resource: Any, **kwargs: Any
    ) -> Any:
        if request.method == "POST":
            return await self._handle_create(request, resource)
        return await self.form_renderer.render_create(request, resource)

    async def _handle_create(self, request: StarletteRequest, resource: Any) -> Any:
        from lexigram.admin.resources.base import Resource

        form = request.scope.get("admin_form_data") or await request.form()
        data = dict(form)
        data.pop("csrf_token", None)

        if isinstance(resource, Resource) and resource._data_source:
            validation = await resource.before_validate(data)
            if validation.is_err():
                error = validation.unwrap_err()
                return await self.form_renderer.render_create(
                    request, resource, errors=_validation_errors_to_dict(error)
                )

            validated_data = validation.unwrap()
            validated = await resource.before_create(validated_data)
            record = await resource._data_source.create(validated)
            await resource.after_create(record)

            resource_prefix = request.scope.get(
                "admin_resource_prefix", resource.name or ""
            )

            from starlette.responses import HTMLResponse

            return HTMLResponse(
                f'<html><head><meta http-equiv="refresh" content="0;url=/admin/{resource_prefix}"></head><body></body></html>'
            )

        return await self.form_renderer.render_create(request, resource)


class EditActionHandler:
    def __init__(self, form_renderer: Any):
        self.form_renderer = form_renderer

    def can_handle(self, action: str) -> bool:
        return action == "edit"

    async def handle(
        self, request: StarletteRequest, resource: Any, **kwargs: Any
    ) -> Any:
        item_id = request.path_params.get("id", "?")
        if request.method == "POST":
            return await self._handle_update(request, resource, item_id)
        return await self.form_renderer.render_edit(request, resource, item_id)

    async def _handle_update(
        self, request: StarletteRequest, resource: Any, item_id: str
    ) -> Any:
        from lexigram.admin.resources.base import Resource

        form = request.scope.get("admin_form_data") or await request.form()
        data = dict(form)
        data.pop("csrf_token", None)

        if isinstance(resource, Resource) and resource._data_source:
            validation = await resource.before_validate(data)
            if validation.is_err():
                error = validation.unwrap_err()
                return await self.form_renderer.render_edit(
                    request,
                    resource,
                    item_id,
                    errors=_validation_errors_to_dict(error),
                )

            validated_data = validation.unwrap()
            validated = await resource.before_update(item_id, validated_data)
            record = await resource._data_source.find_one(item_id)
            can_update = getattr(resource, "can_update", None)
            if can_update and not can_update(record):
                return HTMLResponse("This record cannot be updated", status_code=403)
            updated_record = await resource._data_source.update(item_id, validated)
            await resource.after_update(updated_record)

            resource_prefix = request.scope.get(
                "admin_resource_prefix", resource.name or ""
            )

            return HTMLResponse(
                f'<html><head><meta http-equiv="refresh" content="0;url=/admin/{resource_prefix}"></head><body></body></html>'
            )

        return await self.form_renderer.render_edit(request, resource, item_id)


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
        resource_prefix = request.scope.get(
            "admin_resource_prefix", resource.name or ""
        )
        from starlette.responses import RedirectResponse

        return RedirectResponse(
            url=f"/admin/{resource_prefix}/{new_id}/edit",
            status_code=302,
        )


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

        restored = await resource.restore(item_id)
        new_id = str(getattr(restored, "id", "?"))
        resource_prefix = request.scope.get(
            "admin_resource_prefix", resource.name or ""
        )
        from starlette.responses import RedirectResponse

        return RedirectResponse(
            url=f"/admin/{resource_prefix}/{new_id}/edit",
            status_code=302,
        )


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

        await resource.purge(item_id)
        resource_prefix = request.scope.get(
            "admin_resource_prefix", resource.name or ""
        )
        from starlette.responses import RedirectResponse

        return RedirectResponse(
            url=f"/admin/{resource_prefix}",
            status_code=302,
        )


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

        if isinstance(resource, AdminResource) and resource._data_source:
            try:
                item = await resource._data_source.find_one(item_id)
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

        resource_prefix = request.scope.get("admin_resource_prefix", "")
        delete_url = f"/admin/{resource_prefix}/{item_id}/delete"

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

        if isinstance(resource, AdminResource) and resource._data_source:
            item = await resource._data_source.find_one(item_id)
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
                    '<html><head><meta http-equiv="refresh" content="0;url=/admin/"></head>'
                    "<body>This record cannot be deleted</body></html>",
                    status_code=409,
                )

            success = await resource._data_source.delete(item_id)
            if not success:
                return HTMLResponse("Not found", status_code=404)

            after_delete = getattr(resource, "after_delete", None)
            if after_delete:
                await after_delete(item_id)

            is_htmx = request.headers.get("HX-Request") == "true"
            resource_prefix = request.scope.get("admin_resource_prefix", "")

            if is_htmx:
                response = HTMLResponse("")
                response.headers["HX-Trigger"] = (
                    '{"refresh-list":true,"show-toast":{"message":"Deleted successfully","type":"success"}}'
                )
                response.headers["HX-Redirect"] = f"/admin/{resource_prefix}"
                return response

            return HTMLResponse(
                f'<html><head><meta http-equiv="refresh" content="0;url=/admin/{resource_prefix}"></head><body></body></html>'
            )

        return HTMLResponse("Delete not supported", status_code=400)
