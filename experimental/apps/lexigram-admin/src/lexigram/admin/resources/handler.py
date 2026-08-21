from __future__ import annotations

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
    ResourceActionHandler,
    RestoreActionHandler,
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
        data_source = getattr(resource, "_data_source", None)
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
        prefix = request.scope.get("admin_resource_prefix", resource.name or "")

        from lexigram.admin.resources.permissions_renderer import (
            UserPermissionsRenderer,
        )

        renderer = UserPermissionsRenderer(resource_name=resource.name or "")
        return renderer.render_form(
            request=request,
            user=user,
            inventory=self._permission_inventory(resource),
            item_id=item_id,
            prefix=prefix,
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
        prefix = request.scope.get("admin_resource_prefix", resource.name or "")
        if user is None:
            return RedirectResponse(
                url=f"/admin/{prefix}?error=User not found.", status_code=302
            )
        await data_source.update(item_id, {"permissions": permissions})
        return RedirectResponse(
            url=f"/admin/{prefix}?notice=User permissions updated.",
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

        if not isinstance(resource, AdminResource) or not resource._data_source:
            return HTMLResponse(
                "<h1>Bulk actions not supported for this resource</h1>",
                status_code=400,
            )

        # ── Bulk confirmation (GET) ──
        if request.method == "GET":
            ids = request.query_params.getlist("ids")
            record_count = len(ids)
            resource_prefix = request.scope.get(
                "admin_resource_prefix", resource.name or ""
            )
            bulk_url = f"/admin/{resource_prefix}/bulk"
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
        action_name = form.get("action", "")
        form_ids = form.getlist("ids") if hasattr(form, "getlist") else []

        if not form_ids:
            return HTMLResponse("No records selected", status_code=400)

        is_htmx = request.headers.get("HX-Request") == "true"

        if action_name == "delete":
            count = await resource._data_source.bulk_delete(form_ids)
            message = f"Deleted {count} item(s)"
        elif action_name == "purge":
            count = await resource._data_source.bulk_delete(form_ids)
            message = f"Purged {count} item(s)"
        elif action_name == "restore":
            count = 0
            for item_id in form_ids:
                updated = await resource._data_source.update(
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
        resource_prefix = request.scope.get(
            "admin_resource_prefix", resource.name or ""
        )
        return RedirectResponse(url=f"/admin/{resource_prefix}", status_code=302)


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
            ImportActionHandler(),
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
        resource = self._resources.get(self.name) if self._resources else None
        response = await self._registry.handle(request, resource, self.action)
        await response(scope, receive, send)
