from __future__ import annotations

import inspect
from typing import Any

from starlette.requests import Request as StarletteRequest
from starlette.responses import HTMLResponse, RedirectResponse

from lexigram.admin.config import AdminConfig
from lexigram.di.decorators import inject
from lexigram.logging import get_logger

logger = get_logger(__name__)

from lexigram.admin.resources.action_handlers import (
    CloneActionHandler,
    CreateActionHandler,
    DeleteActionHandler,
    DetailActionHandler,
    EditActionHandler,
    ImportActionHandler,
    ListActionHandler,
    PurgeActionHandler,
    RelationOptionsActionHandler,
    ResourceActionHandler,
    RestoreActionHandler,
)
from lexigram.admin.resources.data_access import get_resource_data_source
from lexigram.admin.resources.urls import (
    admin_prefix_from_request,
    admin_url,
)


class UserPermissionsActionHandler:
    """Handler for the per-user direct permission editing page (users only)."""

    def __init__(self, config: AdminConfig) -> None:
        """Initialize the handler.

        Args:
            config: Admin configuration (used for the CSRF secret).
        """
        self._config = config

    def can_handle(self, action: str) -> bool:
        """Whether this handler serves the given route action."""
        return action == "permissions"

    async def handle(
        self, request: StarletteRequest, resource: Any, **kwargs: Any
    ) -> Any:
        """Serve GET (form) and POST (save) for user permissions.

        Only :class:`~lexigram.admin.resources.users.UserResource`
        instances support the page; other resources get a 404.
        """
        from lexigram.admin.resources.users import UserResource

        if not isinstance(resource, UserResource):
            return HTMLResponse(
                "<h1>Permissions not supported for this resource</h1>",
                status_code=404,
            )
        item_id = request.path_params.get("id", "?")
        data_source = get_resource_data_source(resource)
        if data_source is None:
            return HTMLResponse("Permissions not available", status_code=400)

        if request.method == "POST":
            return await self._handle_submit(request, resource, data_source, item_id)
        return await self._handle_form(request, resource, data_source, item_id)

    async def _handle_form(
        self,
        request: StarletteRequest,
        resource: Any,
        data_source: Any,
        item_id: str,
    ) -> Any:
        """Render the permission checkboxes for one user."""
        user = await data_source.find_one(item_id)
        if user is None:
            return HTMLResponse("<h1>User not found</h1>", status_code=404)

        self._ensure_csrf_token(request)

        from lexigram.admin.resources.permissions_renderer import (
            UserPermissionsRenderer,
        )

        renderer = UserPermissionsRenderer(resource_name=resource.name or "")
        return renderer.render_form(
            request=request,
            user=user,
            inventory=self._permission_inventory(resource),
            item_id=item_id,
        )

    async def _handle_submit(
        self,
        request: StarletteRequest,
        resource: Any,
        data_source: Any,
        item_id: str,
    ) -> Any:
        """Persist the submitted direct permissions for one user."""
        form = request.scope.get("admin_form_data") or await request.form()
        permissions = sorted(
            {str(v).strip() for v in form.getlist("permissions") if str(v).strip()}
        )

        user = await data_source.find_one(item_id)
        if user is None:
            return RedirectResponse(
                url=admin_url(
                    admin_prefix_from_request(request),
                    resource.name or "",
                    suffix="",
                    query="error=User not found.",
                ),
                status_code=302,
            )
        await data_source.update(item_id, {"permissions": permissions})
        return RedirectResponse(
            url=admin_url(
                admin_prefix_from_request(request),
                resource.name or "",
                query="notice=User permissions updated.",
            ),
            status_code=302,
        )

    def _permission_inventory(self, resource: Any) -> Any:
        """Return the grouped permission inventory for the form.

        Uses the inventory wired onto the resource at mount time; falls
        back to a local inventory scoped to the resource's own name.
        """
        inventory = getattr(resource, "permission_inventory", None)
        if inventory is not None:
            return inventory
        from lexigram.admin.rbac.inventory import PermissionInventoryService

        logger.debug(
            "admin.user_permissions_inventory_fallback",
            resource=resource.name,
        )
        fallback = PermissionInventoryService()
        fallback.register_resources([resource.name or "users"])
        return fallback

    def _ensure_csrf_token(self, request: StarletteRequest) -> None:
        """Ensure ``request.state.csrf_token`` exists for the form embed."""
        if getattr(getattr(request, "state", None), "csrf_token", None):
            return
        from lexigram.admin.auth.services.csrf_service import AdminCsrfService

        session = getattr(request, "session", {})
        session_id = session.get("csrf_session_id") or session.get(
            "admin_user_id", "anonymous"
        )
        request.state.csrf_token = AdminCsrfService(
            secret=self._config.auth.session_secret.get_secret_value()
        ).generate_token(session_id)


class BulkActionHandler:
    """Handler for the ``bulk`` action — processes bulk operations."""

    _CONFIRM_LABELS = {
        "bulk-delete-confirm": ("delete", "Delete", "DELETE"),
        "bulk-purge-confirm": ("purge", "Purge", "PURGE"),
        "bulk-restore-confirm": ("restore", "Restore", "RESTORE"),
    }

    def can_handle(self, action: str) -> bool:
        return action in (
            "bulk",
            "bulk-delete-confirm",
            "bulk-purge-confirm",
            "bulk-restore-confirm",
        )

    async def handle(
        self, request: StarletteRequest, resource: Any, **kwargs: Any
    ) -> Any:
        from lexigram.admin.resources.base import Resource as AdminResource
        from lexigram.admin.ui.organisms.admin_slide_over import (
            render_bulk_delete_confirm,
        )

        data_source = get_resource_data_source(resource)
        if not isinstance(resource, AdminResource) or data_source is None:
            return HTMLResponse(
                "<h1>Bulk actions not supported for this resource</h1>",
                status_code=400,
            )

        # ── Bulk confirmation (GET) ──
        if request.method == "GET":
            ids = request.query_params.getlist("ids")
            record_count = len(ids)
            bulk_url = admin_url(
                admin_prefix_from_request(request),
                resource.name or "",
                "bulk",
            )
            confirm_action = request.scope.get("admin_action", "bulk-delete-confirm")
            action, confirm_label, confirm_phrase = self._CONFIRM_LABELS.get(
                confirm_action, ("delete", "Delete", "DELETE")
            )
            html = render_bulk_delete_confirm(
                record_count=record_count,
                bulk_url=bulk_url,
                action=action,
                confirm_label=confirm_label,
                confirm_phrase=confirm_phrase,
            )
            return HTMLResponse(html)

        # ── Bulk action execution (POST) ──
        form = request.scope.get("admin_form_data")
        if form is None:
            form = await request.form()
        action_name = str(form.get("action", "") or "")
        form_ids = form.getlist("ids") if hasattr(form, "getlist") else []

        # Authorization for the generic endpoint is view-level so safe bulk
        # actions (such as export) remain available. Enforce the submitted
        # mutating action here as well, including legacy resource hooks.
        required_capability = {
            "delete": "can_delete",
            "purge": "can_delete",
            "restore": "can_update",
        }.get(action_name)
        if required_capability:
            capabilities = getattr(getattr(request, "state", None), "permissions", None)
            if isinstance(capabilities, dict) and not capabilities.get(required_capability, False):
                return HTMLResponse("Forbidden", status_code=403)
            hook_name = (
                "has_delete_permission"
                if required_capability == "can_delete"
                else "has_change_permission"
            )
            hook = getattr(resource, hook_name, None)
            if callable(hook):
                allowed = hook(getattr(getattr(request, "state", None), "user", None))
                if inspect.isawaitable(allowed):
                    allowed = await allowed
                if not allowed:
                    return HTMLResponse("Forbidden", status_code=403)

        if not form_ids:
            return HTMLResponse("No records selected", status_code=400)

        is_htmx = request.headers.get("HX-Request") == "true"

        # Bulk UI visibility is not authorization. Mirror the single-record
        # delete guard for every selected record before performing any write,
        # so a protected row cannot be deleted through the bulk endpoint.
        if action_name in {"delete", "purge"}:
            can_delete = getattr(resource, "can_delete", None)
            if can_delete:
                for item_id in form_ids:
                    item = await data_source.find_one(item_id)
                    if item is not None and not can_delete(item):
                        message = "One or more selected records cannot be deleted"
                        if is_htmx:
                            response = HTMLResponse("", status_code=409)
                            response.headers["HX-Trigger"] = (
                                '{"show-toast":{"message":"'
                                + message
                                + '","type":"error"}}'
                            )
                            return response
                        return HTMLResponse(message, status_code=409)

        if action_name == "delete":
            count = await data_source.bulk_delete(form_ids)
            message = f"Deleted {count} item(s)"
        elif action_name == "purge":
            count = await data_source.bulk_delete(form_ids)
            message = f"Purged {count} item(s)"
        elif action_name in {"export", "export_csv"}:
            import csv
            from io import StringIO

            records = []
            for item_id in form_ids:
                item = await data_source.find_one(item_id)
                if item is None:
                    continue
                if isinstance(item, dict):
                    records.append(dict(item))
                elif hasattr(item, "model_dump"):
                    records.append(dict(item.model_dump()))
                elif hasattr(item, "dict") and callable(item.dict):
                    records.append(dict(item.dict()))
                else:
                    records.append(dict(vars(item)))

            fieldnames: list[str] = []
            for record in records:
                for key in record:
                    if key not in fieldnames:
                        fieldnames.append(str(key))
            output = StringIO()
            if fieldnames:
                writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(records)
            filename = f"{resource.name or 'records'}-export.csv"
            response = HTMLResponse(output.getvalue(), media_type="text/csv")
            response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
            if is_htmx:
                # An HTMX swap must not put CSV bytes into the table. A
                # non-HTMX submission downloads normally; callers using HTMX
                # can consume the response as a download in their event hook.
                response.headers["HX-Reswap"] = "none"
            return response
        elif action_name == "restore":
            can_update = getattr(resource, "can_update", None)
            if can_update:
                for item_id in form_ids:
                    item = await data_source.find_one(item_id)
                    if item is not None and not can_update(item):
                        message = "One or more selected records cannot be restored"
                        if is_htmx:
                            response = HTMLResponse("", status_code=409)
                            response.headers["HX-Trigger"] = (
                                '{"show-toast":{"message":"'
                                + message
                                + '","type":"error"}}'
                            )
                            return response
                        return HTMLResponse(message, status_code=409)
            count = 0
            for item_id in form_ids:
                updated = await data_source.update(
                    item_id, {"deleted_at": None}
                )
                if updated is not None:
                    count += 1
            message = f"Restored {count} item(s)"
        else:
            return HTMLResponse(f"Unknown action: {action_name}", status_code=400)

        if is_htmx:
            response = HTMLResponse(f"<p>{message}</p>")
            response.headers["HX-Trigger"] = (
                '{"refresh-list":true,"show-toast":{"message":"'
                + message.replace('"', '\\"')
                + '","type":"success"}}'
            )
            return response
        return RedirectResponse(
            url=admin_url(
                admin_prefix_from_request(request),
                resource.name or "",
            ),
            status_code=302,
        )


class DefaultActionHandler:
    def can_handle(self, action: str) -> bool:
        return True

    async def handle(
        self, request: StarletteRequest, resource: Any, **kwargs: Any
    ) -> Any:
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
        form_renderer = FormRenderer(
            self._config,
            self.name,
            renderer,
            resources=self._resources,
        )

        self._handlers = [
            ListActionHandler(list_renderer),
            DetailActionHandler(detail_renderer),
            CreateActionHandler(form_renderer),
            EditActionHandler(form_renderer),
            CloneActionHandler(),
            RestoreActionHandler(),
            PurgeActionHandler(),
            DeleteActionHandler(),
            ImportActionHandler(),
            RelationOptionsActionHandler(self._resources),
            UserPermissionsActionHandler(self._config),
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

    async def __call__(self, scope: Any, receive: Any, send: Any) -> Any:
        request = StarletteRequest(scope, receive, send)
        scope["admin_resource_prefix"] = self.name
        scope["admin_action"] = self.action
        scope["admin_prefix"] = self._config.prefix.rstrip("/")
        resource = self._resources.get(self.name) if self._resources else None
        if resource is not None:
            permission_method = {
                "list": "has_view_permission",
                "detail": "has_view_permission",
                "relation-options": "has_view_permission",
                "create": "has_add_permission",
                "import-example": "has_add_permission",
                "import-report": "has_view_permission",
                "clone": "has_add_permission",
                "edit": "has_change_permission",
                "restore": "has_change_permission",
                "permissions": "has_change_permission",
                "delete": "has_delete_permission",
                "delete-confirm": "has_delete_permission",
                "purge": "has_delete_permission",
                # The generic endpoint also handles non-destructive bulk
                # actions (for example export); the handler checks the
                # submitted action's capability after parsing the form.
                "bulk": "has_view_permission",
                "bulk-delete-confirm": "has_delete_permission",
                "bulk-purge-confirm": "has_delete_permission",
                "bulk-restore-confirm": "has_change_permission",
            }.get(self.action)
            checker = getattr(resource, permission_method, None) if permission_method else None
            if callable(checker):
                user = getattr(request.state, "user", None)
                allowed = checker(user)
                if inspect.isawaitable(allowed):
                    allowed = await allowed
                if not allowed:
                    response = HTMLResponse("Forbidden", status_code=403)
                    await response(scope, receive, send)
                    return
        response = await self._registry.handle(request, resource, self.action)
        await response(scope, receive, send)
