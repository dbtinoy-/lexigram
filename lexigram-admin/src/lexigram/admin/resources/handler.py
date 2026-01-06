from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from decimal import InvalidOperation as DecimalInvalidOp
from enum import Enum
import types
from typing import Any, Protocol, Union, get_args, get_origin, get_type_hints
from uuid import UUID

from starlette.requests import Request as StarletteRequest
from starlette.responses import HTMLResponse, RedirectResponse

from lexigram.admin.config import AdminConfig
from lexigram.di.decorators import inject
from lexigram.logging import get_logger

logger = get_logger(__name__)


def _unwrap_optional(tp: type) -> type:
    """Unwrap Optional[T] or T | None to T."""
    origin = get_origin(tp)
    if origin in (Union, types.UnionType):
        non_none = [a for a in get_args(tp) if a is not type(None)]
        if len(non_none) == 1:
            return non_none[0]
    return tp


def _coerce_form_data(data: dict, model: type | None) -> dict:
    """Convert HTML form string values to proper Python types."""
    if model is None:
        return data
    try:
        hints = get_type_hints(model)
    except Exception:
        return data

    for key, value in list(data.items()):
        if key not in hints:
            continue
        if not isinstance(value, str):
            continue

        expected = _unwrap_optional(hints[key])
        origin = get_origin(expected)
        if expected is bool:
            data[key] = value == "on"
        elif expected is int:
            try:
                data[key] = int(value)
            except (ValueError, TypeError):
                pass
        elif expected is float:
            if value == "":
                data[key] = None
            else:
                try:
                    data[key] = float(value)
                except (ValueError, TypeError):
                    pass
        elif expected is Decimal:
            if value == "":
                data[key] = None
            else:
                try:
                    data[key] = Decimal(value)
                except (DecimalInvalidOp, ValueError, TypeError):
                    pass
        elif expected is UUID:
            if value == "":
                data[key] = None
            else:
                try:
                    data[key] = UUID(value)
                except (ValueError, AttributeError):
                    pass
        elif expected is datetime:
            if value == "":
                data[key] = None
            else:
                try:
                    data[key] = datetime.fromisoformat(value.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pass
        elif expected is date:
            if value == "":
                data[key] = None
            else:
                try:
                    data[key] = date.fromisoformat(value)
                except (ValueError, TypeError):
                    pass
        elif origin is list:
            if value == "":
                data[key] = []
            else:
                args = get_args(expected)
                inner = args[0] if args else str
                items = [s.strip() for s in value.split(",")]
                if inner is not str:
                    try:
                        data[key] = [inner(item) for item in items]
                    except (ValueError, TypeError):
                        pass
                else:
                    data[key] = items
        elif isinstance(expected, type) and issubclass(expected, Enum):
            if value != "":
                try:
                    data[key] = expected(value)
                except (ValueError, TypeError):
                    pass
        elif origin is dict:
            if value != "":
                try:
                    from lexigram.serialization import loads_str as _json_loads

                    data[key] = _json_loads(value)
                except Exception:
                    pass

    return data


def _validation_errors_to_dict(error: Any) -> dict[str, list[str]]:
    """Convert AdminValidationError.errors (list[FieldError]) to dict form."""
    errors: dict[str, list[str]] = {}
    for fe in error.errors:
        errors.setdefault(fe.field, []).append(fe.message)
    return errors


class ResourceActionHandler(Protocol):
    """Protocol for action handlers."""

    def can_handle(self, action: str) -> bool: ...

    async def handle(
        self, request: StarletteRequest, resource: Any, **kwargs
    ) -> Any: ...


class ListActionHandler:
    def __init__(self, list_renderer: Any):
        self.list_renderer = list_renderer

    def can_handle(self, action: str) -> bool:
        return action == "list"

    async def handle(self, request: StarletteRequest, resource: Any, **kwargs) -> Any:
        return await self.list_renderer.render(request, resource)


class DetailActionHandler:
    def __init__(self, detail_renderer: Any):
        self.detail_renderer = detail_renderer

    def can_handle(self, action: str) -> bool:
        return action == "detail"

    async def handle(self, request: StarletteRequest, resource: Any, **kwargs) -> Any:
        item_id = request.path_params.get("id", "?")
        return await self.detail_renderer.render_detail(request, resource, item_id)


class CreateActionHandler:
    def __init__(self, form_renderer: Any):
        self.form_renderer = form_renderer

    def can_handle(self, action: str) -> bool:
        return action == "create"

    async def handle(self, request: StarletteRequest, resource: Any, **kwargs) -> Any:
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

    async def handle(self, request: StarletteRequest, resource: Any, **kwargs) -> Any:
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
            record = await resource._data_source.update(item_id, validated)
            await resource.after_update(record)

            resource_prefix = request.scope.get(
                "admin_resource_prefix", resource.name or ""
            )

            from starlette.responses import HTMLResponse

            return HTMLResponse(
                f'<html><head><meta http-equiv="refresh" content="0;url=/admin/{resource_prefix}"></head><body></body></html>'
            )

        return await self.form_renderer.render_edit(request, resource, item_id)


class CloneActionHandler:
    """Handler for the ``clone`` action — duplicates a record and redirects."""

    def can_handle(self, action: str) -> bool:
        return action == "clone"

    async def handle(self, request: StarletteRequest, resource: Any, **kwargs) -> Any:
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

    async def handle(self, request: StarletteRequest, resource: Any, **kwargs) -> Any:
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

    async def handle(self, request: StarletteRequest, resource: Any, **kwargs) -> Any:
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


class DeleteActionHandler:
    """Handler for delete-confirm and delete actions."""

    def can_handle(self, action: str) -> bool:
        return action in ("delete-confirm", "delete")

    async def handle(self, request: StarletteRequest, resource: Any, **kwargs) -> Any:
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
            except Exception:
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


class BulkActionHandler:
    """Handler for the ``bulk`` action — processes bulk operations."""

    def can_handle(self, action: str) -> bool:
        return action in ("bulk", "bulk-delete-confirm")

    async def handle(self, request: StarletteRequest, resource: Any, **kwargs) -> Any:
        from lexigram.admin.resources.base import Resource as AdminResource
        from lexigram.admin.ui.organisms.admin_slide_over import (
            render_bulk_delete_confirm,
        )

        if not isinstance(resource, AdminResource) or not resource._data_source:
            return HTMLResponse(
                "<h1>Bulk actions not supported for this resource</h1>",
                status_code=400,
            )

        # ── Bulk delete confirmation (GET) ──
        if request.method == "GET":
            ids = request.query_params.getlist("ids")
            record_count = len(ids)
            resource_prefix = request.scope.get("admin_resource_prefix", resource.name or "")
            bulk_url = f"/admin/{resource_prefix}/bulk"
            html = render_bulk_delete_confirm(
                record_count=record_count,
                bulk_url=bulk_url,
            )
            return HTMLResponse(html)

        # ── Bulk action execution (POST) ──
        form = await request.form()
        action_name = form.get("action", "")
        ids = form.getlist("ids") if hasattr(form, "getlist") else []

        if not ids:
            return HTMLResponse("No records selected", status_code=400)

        is_htmx = request.headers.get("HX-Request") == "true"

        if action_name == "delete":
            count = await resource._data_source.bulk_delete(ids)
            message = f"Deleted {count} item(s)"

            if is_htmx:
                response = HTMLResponse(f"<p>{message}</p>")
                response.headers["HX-Trigger"] = (
                    '{"refresh-list":true,"show-toast":{"message":"'
                    + message.replace('"', '\\"')
                    + '","type":"success"}}'
                )
                return response
            resource_prefix = request.scope.get(
                "admin_resource_prefix", resource.name or ""
            )
            return RedirectResponse(url=f"/admin/{resource_prefix}", status_code=302)

        return HTMLResponse(f"Unknown action: {action_name}", status_code=400)


class DefaultActionHandler:
    def can_handle(self, action: str) -> bool:
        return True

    async def handle(self, request: StarletteRequest, resource: Any, **kwargs) -> Any:
        return HTMLResponse("<h1>Unknown action</h1>")


class ActionHandlerRegistry:
    """Registry for action handlers."""

    def __init__(self, config: AdminConfig, name: str, resources: dict | None = None):
        self._config = config
        self.name = name
        self._resources = resources or {}
        self._handlers: list[ResourceActionHandler] = []
        self._initialize_handlers()

    def _initialize_handlers(self) -> None:
        from lexigram.admin.engine.renderer import AdminRenderer as EngineAdminRenderer
        from lexigram.admin.resources.detail_renderer import DetailRenderer
        from lexigram.admin.resources.form_renderer import FormRenderer
        from lexigram.admin.resources.list_renderer import ListRenderer

        # AdminRenderer is stateless — nav is resolved from request.app.state at
        # render time, so a fresh instance per handler registry is safe.
        renderer = EngineAdminRenderer()

        list_renderer = ListRenderer(self._config, self.name, renderer)
        detail_renderer = DetailRenderer(self._config, self.name, renderer)
        form_renderer = FormRenderer(self._config, self.name, renderer)

        self._handlers = [
            ListActionHandler(list_renderer),
            DetailActionHandler(detail_renderer),
            CreateActionHandler(form_renderer),
            EditActionHandler(form_renderer),
            CloneActionHandler(),
            RestoreActionHandler(),
            PurgeActionHandler(),
            DeleteActionHandler(),
            BulkActionHandler(),
            DefaultActionHandler(),
        ]

    async def handle(
        self, request: StarletteRequest, resource: Any, action: str
    ) -> Any:
        for handler in self._handlers:
            if handler.can_handle(action):
                return await handler.handle(request, resource)
        return HTMLResponse("<h1>Unknown action</h1>")


@inject
class ResourceHandler:
    """Handler for resource routes."""

    def __init__(
        self,
        config: AdminConfig,
        name: str,
        action: str,
        resources: dict | None = None,
    ):
        self._config = config
        self.name = name
        self.action = action
        self._resources = resources or {}
        self._registry = ActionHandlerRegistry(config, name, resources=self._resources)

    async def __call__(self, scope, receive, send) -> Any:
        request = StarletteRequest(scope, receive, send)
        scope["admin_resource_prefix"] = self.name
        resource = self._resources.get(self.name) if self._resources else None
        response = await self._registry.handle(request, resource, self.action)
        await response(scope, receive, send)
