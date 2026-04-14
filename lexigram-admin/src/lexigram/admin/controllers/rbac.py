"""RBAC management controller: roles CRUD and user role assignment.

Standalone pages (no admin shell), mirroring the AuthController pattern:
CSRF-protected forms, flash-message redirects, and grouped permission
checkboxes built from a built-in resource × action inventory.
"""

from __future__ import annotations

import secrets
from typing import Any
from urllib.parse import quote_plus

from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse

from lexigram.admin.auth.protocols import AdminCsrfServiceProtocol
from lexigram.admin.auth.store.protocols import AdminUserStoreProtocol
from lexigram.admin.controllers.base import AdminController
from lexigram.admin.engine.renderer import AdminRenderer
from lexigram.admin.lib.template import (
    render_role_form_page,
    render_roles_list_page,
    render_user_roles_page,
    render_users_list_page,
)
from lexigram.admin.rbac.protocols import AdminRoleServiceProtocol
from lexigram.contracts.web import get, post
from lexigram.di.decorators import inject
from lexigram.logging import get_logger

logger = get_logger(__name__)

_RBAC_RESOURCES: tuple[str, ...] = ("roles", "users", "settings")
_RBAC_ACTIONS: tuple[str, ...] = (
    "list",
    "view",
    "create",
    "update",
    "delete",
    "export",
)


def _permission_options() -> dict[str, list[str]]:
    """Grouped permission inventory: ``{resource: ["resource.action", ...]}``.

    Returns:
        Mapping of built-in resource to its listable permission strings.
    """
    return {
        resource: [f"{resource}.{action}" for action in _RBAC_ACTIONS]
        for resource in _RBAC_RESOURCES
    }


@inject
class RbacController(AdminController):
    """RBAC management pages (roles CRUD + user role assignment)."""

    prefix = ""

    def __init__(
        self,
        csrf_service: AdminCsrfServiceProtocol,
        renderer: AdminRenderer,
        role_service: AdminRoleServiceProtocol | None = None,
        user_store: AdminUserStoreProtocol | None = None,
        task_manager: object | None = None,
    ) -> None:
        """Initialise the RBAC controller.

        Args:
            csrf_service: Generates and validates CSRF tokens.
            renderer: AdminRenderer for page rendering.
            role_service: Role CRUD orchestrator; ``None`` renders pages
                without persistence wiring.
            user_store: Admin user persistence for the users pages.
            task_manager: Optional task manager (unused by this controller).
        """
        super().__init__(renderer, task_manager)
        self._csrf_service = csrf_service
        self._role_service = role_service
        self._user_store = user_store

    # ------------------------------------------------------------------
    # GET /roles — roles list
    # ------------------------------------------------------------------

    @get("/roles")
    async def roles_list(self, request: Request) -> HTMLResponse:
        """Render the roles management list page.

        Args:
            request: Incoming HTTP request (error/notice flash params).

        Returns:
            HTMLResponse with the roles table.
        """
        roles = await self._role_service.list_roles() if self._role_service else []
        html = render_roles_list_page(
            roles,
            error=str(request.query_params.get("error", "")),
            notice=str(request.query_params.get("notice", "")),
        )
        return HTMLResponse(content=html)

    # ------------------------------------------------------------------
    # GET/POST /roles/new — create form
    # ------------------------------------------------------------------

    @get("/roles/new")
    async def role_new_form(self, request: Request) -> HTMLResponse:
        """Render the role creation form.

        Args:
            request: Incoming HTTP request.

        Returns:
            HTMLResponse with the create-role form.
        """
        csrf_token = self._get_csrf_token(request)
        html = render_role_form_page(
            permission_options=_permission_options(),
            error=str(request.query_params.get("error", "")),
            notice=str(request.query_params.get("notice", "")),
            csrf_token=csrf_token,
        )
        return HTMLResponse(content=html)

    @post("/roles/new")
    async def role_new_submit(self, request: Request) -> RedirectResponse:
        """Create a role from the form payload.

        Args:
            request: Incoming HTTP request carrying form data.

        Returns:
            RedirectResponse with ``notice`` or ``error`` flash.
        """
        form = await request.form()
        if not self._csrf_ok(request, str(form.get("csrf_token", ""))):
            return self._error_redirect(
                "/admin/roles/new",
                "Invalid or expired security token. Please try again.",
            )
        name = str(form.get("name", "")).strip()
        description = str(form.get("description", "")).strip()
        permissions = self._collect_permissions(form)
        if not name:
            return self._error_redirect("/admin/roles/new", "Role name is required.")

        if self._role_service is not None:
            result = await self._role_service.create_role(
                name, description, permissions, []
            )
            if result.is_err():
                return self._error_redirect(
                    "/admin/roles/new", str(result.unwrap_err())
                )
        return RedirectResponse(
            url="/admin/roles?notice=Role created.", status_code=302
        )

    # ------------------------------------------------------------------
    # GET/POST /roles/{name}/edit — edit form
    # ------------------------------------------------------------------

    @get("/roles/{name}/edit")
    async def role_edit_form(self, request: Request) -> HTMLResponse:
        """Render the role edit form with permissions pre-checked.

        Args:
            request: Incoming HTTP request (role name in path).

        Returns:
            HTMLResponse with the edit-role form.
        """
        name = request.path_params.get("name", "")
        role = None
        if self._role_service is not None:
            roles = await self._role_service.list_roles()
            role = next((r for r in roles if r.name == name), None)
        csrf_token = self._get_csrf_token(request)
        html = render_role_form_page(
            role=role,
            permission_options=_permission_options(),
            selected=set(role.permissions) if role else set(),
            error=str(request.query_params.get("error", "")),
            csrf_token=csrf_token,
        )
        return HTMLResponse(content=html)

    @post("/roles/{name}/edit")
    async def role_edit_submit(self, request: Request) -> RedirectResponse:
        """Update a role from the form payload.

        Args:
            request: Incoming HTTP request carrying form data.

        Returns:
            RedirectResponse with ``notice`` or ``error`` flash.
        """
        form = await request.form()
        if not self._csrf_ok(request, str(form.get("csrf_token", ""))):
            return self._error_redirect(
                "/admin/roles", "Invalid or expired security token. Please try again."
            )
        name = str(form.get("name", "")).strip() or str(
            request.path_params.get("name", "")
        )
        description = str(form.get("description", "")).strip()
        permissions = self._collect_permissions(form)

        if self._role_service is not None:
            result = await self._role_service.update_role(
                name, description, permissions, []
            )
            if result.is_err():
                return self._error_redirect(
                    f"/admin/roles/{name}/edit", str(result.unwrap_err())
                )
        return RedirectResponse(
            url="/admin/roles?notice=Role updated.", status_code=302
        )

    # ------------------------------------------------------------------
    # POST /roles/{name}/delete — delete
    # ------------------------------------------------------------------

    @post("/roles/{name}/delete")
    async def role_delete_submit(self, request: Request) -> RedirectResponse:
        """Delete a role (system roles are rejected by the service).

        Args:
            request: Incoming HTTP request (role name in path).

        Returns:
            RedirectResponse with ``notice`` or ``error`` flash.
        """
        form = await request.form()
        if not self._csrf_ok(request, str(form.get("csrf_token", ""))):
            return self._error_redirect(
                "/admin/roles", "Invalid or expired security token. Please try again."
            )
        name = str(request.path_params.get("name", ""))
        if self._role_service is not None:
            result = await self._role_service.delete_role(name)
            if result.is_err():
                return self._error_redirect("/admin/roles", str(result.unwrap_err()))
        return RedirectResponse(
            url="/admin/roles?notice=Role deleted.", status_code=302
        )

    # ------------------------------------------------------------------
    # GET /users — users list
    # ------------------------------------------------------------------

    @get("/users")
    async def users_list(self, request: Request) -> HTMLResponse:
        """Render the admin users list page with role badges.

        Args:
            request: Incoming HTTP request.

        Returns:
            HTMLResponse with the users table.
        """
        users = await self._user_store.list_users() if self._user_store else []
        html = render_users_list_page(
            users,
            error=str(request.query_params.get("error", "")),
            notice=str(request.query_params.get("notice", "")),
        )
        return HTMLResponse(content=html)

    # ------------------------------------------------------------------
    # GET/POST /users/{user_id}/roles — user role assignment
    # ------------------------------------------------------------------

    @get("/users/{user_id}/roles")
    async def user_roles_form(self, request: Request) -> HTMLResponse:
        """Render the user role assignment form.

        Args:
            request: Incoming HTTP request (user id in path).

        Returns:
            HTMLResponse with role checkboxes pre-checked from the user.
        """
        user = None
        user_id = str(request.path_params.get("user_id", ""))
        if self._user_store is not None:
            users = await self._user_store.list_users()
            user = next(
                (u for u in users if str(getattr(u, "user_id", "")) == user_id),
                None,
            )
        roles = await self._role_service.list_roles() if self._role_service else []
        csrf_token = self._get_csrf_token(request)
        html = render_user_roles_page(
            user,
            roles,
            role_names=set(getattr(user, "roles", []) if user else []),
            error=str(request.query_params.get("error", "")),
            csrf_token=csrf_token,
        )
        return HTMLResponse(content=html)

    @post("/users/{user_id}/roles")
    async def user_roles_submit(self, request: Request) -> RedirectResponse:
        """Assign roles to a user (persisted via ``update_user``).

        Args:
            request: Incoming HTTP request (user id in path + roles).

        Returns:
            RedirectResponse with ``notice`` or ``error`` flash.
        """
        form = await request.form()
        if not self._csrf_ok(request, str(form.get("csrf_token", ""))):
            return self._error_redirect(
                "/admin/users", "Invalid or expired security token. Please try again."
            )
        user_id = str(request.path_params.get("user_id", ""))
        roles = sorted({str(v) for v in form.getlist("roles")})
        if self._user_store is not None:
            try:
                await self._user_store.update_user(user_id, {"roles": roles})
            except Exception as exc:
                logger.warning("admin.user_roles_update_failed", error=str(exc))
                return self._error_redirect("/admin/users", "Could not update roles.")
        return RedirectResponse(
            url="/admin/users?notice=User roles updated.", status_code=302
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_csrf_token(self, request: Request) -> str:
        """Return a CSRF token, creating and persisting the session id."""
        csrf_session_id = str(request.session.get("csrf_session_id", ""))
        if not csrf_session_id:
            csrf_session_id = secrets.token_hex(16)
            request.session["csrf_session_id"] = csrf_session_id
        return self._csrf_service.generate_token(csrf_session_id)

    def _csrf_ok(self, request: Request, csrf_token: str) -> bool:
        """Validate the submitted CSRF token against the session id.

        Args:
            request: Incoming HTTP request (session already loaded).
            csrf_token: Token submitted with the form.

        Returns:
            ``True`` when the token matches the session.
        """
        csrf_session_id = str(request.session.get("csrf_session_id", ""))
        return bool(
            csrf_session_id
            and self._csrf_service.validate_token(csrf_session_id, csrf_token)
        )

    def _collect_permissions(self, form: Any) -> list[str]:
        """Return sorted, de-duplicated permission strings from the form.

        The inventory whitelist is intentionally NOT enforced here: role
        permissions can legitimately live outside the built-in inventory
        (wildcards like ``"*"``, app-defined strings carried as hidden
        inputs). The controller only normalizes and deduplicates.

        Args:
            form: Parsed form data.

        Returns:
            Sorted unique non-empty permission strings.
        """
        return sorted(
            {str(v).strip() for v in form.getlist("permissions") if str(v).strip()}
        )

    @staticmethod
    def _error_redirect(url: str, message: str) -> RedirectResponse:
        """Return a 302 redirect carrying an error flash message."""
        return RedirectResponse(
            url=f"{url}?error={quote_plus(message)}",
            status_code=302,
        )


__all__ = ["RbacController"]
