"""RBAC management controller: roles CRUD and user role assignment.

Pages render inside the admin shell via the injected AdminRenderer, with
per-route permission gating (``roles.*`` / ``users.*``) and a super-admin
bypass, mirroring the SettingsController pattern: CSRF-protected forms,
flash-message redirects, and grouped permission checkboxes built from a
built-in resource × action inventory.
"""

from __future__ import annotations

from html import escape
import secrets
from typing import Any
from urllib.parse import quote_plus

from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response

from lexigram.admin.auth.protocols import AdminCsrfServiceProtocol
from lexigram.admin.auth.store.protocols import AdminUserStoreProtocol
from lexigram.admin.config import AdminConfig
from lexigram.admin.controllers.base import AdminController
from lexigram.admin.engine.renderer import AdminRenderer
from lexigram.admin.lib.template import (
    render_role_form_page,
    render_roles_list_page,
    render_user_permissions_page,
    render_user_roles_page,
    render_users_list_page,
)
from lexigram.admin.rbac.inventory import PermissionInventoryService
from lexigram.admin.rbac.protocols import AdminRoleServiceProtocol
from lexigram.contracts.web import get, post
from lexigram.di.decorators import inject


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
        inventory: PermissionInventoryService | None = None,
        config: AdminConfig | None = None,
        task_manager: object | None = None,
    ) -> None:
        """Initialise the RBAC controller.

        Args:
            csrf_service: Generates and validates CSRF tokens.
            renderer: AdminRenderer for page rendering.
            role_service: Role CRUD orchestrator; ``None`` renders pages
                without persistence wiring.
            user_store: Admin user persistence for the users pages.
            inventory: Permission inventory backing the permission
                checkboxes; defaults to a builtin-only instance when
                ``None``.
            config: Admin config; ``None`` falls back to the default
                super-admin role name ``"superadmin"``.
            task_manager: Optional task manager (unused by this controller).
        """
        super().__init__(renderer, task_manager)
        self._csrf_service = csrf_service
        self._role_service = role_service
        self._user_store = user_store
        self._inventory = inventory or PermissionInventoryService()
        self._super_admin_role = (
            config.rbac.super_admin_role if config else "superadmin"
        )

    # ------------------------------------------------------------------
    # GET /roles — roles list
    # ------------------------------------------------------------------

    @get("/roles")
    async def roles_list(self, request: Request) -> HTMLResponse:
        """Render the roles management list page.

        Args:
            request: Incoming HTTP request (error/notice flash params).

        Returns:
            HTMLResponse with the roles table inside the admin shell.
        """
        denied = await self._require(request, "roles.list")
        if denied is not None:
            return denied
        roles = await self._role_service.list_roles() if self._role_service else []
        html = render_roles_list_page(
            roles,
            error=str(request.query_params.get("error", "")),
            notice=str(request.query_params.get("notice", "")),
            super_admin_role=self._super_admin_role,
        )
        return await self.render_admin(
            request,
            html,
            title="Roles",
            breadcrumbs=self.generate_breadcrumbs(
                ("Home", "/admin/"),
                current="Roles",
            ),
        )

    # ------------------------------------------------------------------
    # GET/POST /roles/new — create form
    # ------------------------------------------------------------------

    @get("/roles/new")
    async def role_new_form(self, request: Request) -> HTMLResponse:
        """Render the role creation form.

        Args:
            request: Incoming HTTP request.

        Returns:
            HTMLResponse with the create-role form inside the admin shell.
        """
        denied = await self._require(request, "roles.create")
        if denied is not None:
            return denied
        roles = await self._role_service.list_roles() if self._role_service else []
        csrf_token = self._get_csrf_token(request)
        html = render_role_form_page(
            permission_options=self._inventory.options(),
            inherits_options=[r.name for r in roles],
            error=str(request.query_params.get("error", "")),
            notice=str(request.query_params.get("notice", "")),
            csrf_token=csrf_token,
        )
        return await self.render_admin(
            request,
            html,
            title="New Role",
            breadcrumbs=self.generate_breadcrumbs(
                ("Home", "/admin/"),
                ("Roles", "/admin/roles"),
                current="New Role",
            ),
        )

    @post("/roles/new")
    async def role_new_submit(self, request: Request) -> Response:
        """Create a role from the form payload.

        Args:
            request: Incoming HTTP request carrying form data.

        Returns:
            RedirectResponse with ``notice`` or ``error`` flash.
        """
        denied = await self._require(request, "roles.create")
        if denied is not None:
            return denied
        form = await request.form()
        if not self._csrf_ok(request, str(form.get("csrf_token", ""))):
            return self._error_redirect(
                "/admin/roles/new",
                "Invalid or expired security token. Please try again.",
            )
        name = str(form.get("name", "")).strip()
        description = str(form.get("description", "")).strip()
        permissions = self._collect_permissions(form)
        inherits = sorted(
            {str(v).strip() for v in form.getlist("inherits") if str(v).strip()}
        )
        if not name:
            return self._error_redirect("/admin/roles/new", "Role name is required.")

        if self._role_service is not None:
            result = await self._role_service.create_role(
                name, description, permissions, inherits
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
            HTMLResponse with the edit-role form inside the admin shell.
        """
        denied = await self._require(request, "roles.update")
        if denied is not None:
            return denied
        name = request.path_params.get("name", "")
        role = None
        roles: list[Any] = []
        if self._role_service is not None:
            roles = await self._role_service.list_roles()
            role = next((r for r in roles if r.name == name), None)
        csrf_token = self._get_csrf_token(request)
        html = render_role_form_page(
            role=role,
            permission_options=self._inventory.options(),
            selected=set(role.permissions) if role else set(),
            inherits_options=[r.name for r in roles if r.name != name]
            if roles
            else None,
            inherited=set(role.inherits) if role else set(),
            error=str(request.query_params.get("error", "")),
            csrf_token=csrf_token,
            super_admin_role=self._super_admin_role,
        )
        return await self.render_admin(
            request,
            html,
            title="Edit Role",
            breadcrumbs=self.generate_breadcrumbs(
                ("Home", "/admin/"),
                ("Roles", "/admin/roles"),
                current=name,
            ),
        )

    @post("/roles/{name}/edit")
    async def role_edit_submit(self, request: Request) -> Response:
        """Update a role from the form payload.

        Args:
            request: Incoming HTTP request carrying form data.

        Returns:
            RedirectResponse with ``notice`` or ``error`` flash.
        """
        denied = await self._require(request, "roles.update")
        if denied is not None:
            return denied
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
        inherits = sorted(
            {str(v).strip() for v in form.getlist("inherits") if str(v).strip()}
        )

        if self._role_service is not None:
            result = await self._role_service.update_role(
                name, description, permissions, inherits
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
    async def role_delete_submit(self, request: Request) -> Response:
        """Delete a role (system roles are rejected by the service).

        Args:
            request: Incoming HTTP request (role name in path).

        Returns:
            RedirectResponse with ``notice`` or ``error`` flash.
        """
        denied = await self._require(request, "roles.delete")
        if denied is not None:
            return denied
        form = await request.form()
        if not self._csrf_ok(request, str(form.get("csrf_token", ""))):
            return self._error_redirect(
                "/admin/roles", "Invalid or expired security token. Please try again."
            )
        name = str(request.path_params.get("name", ""))
        if name == self._super_admin_role:
            return self._error_redirect(
                "/admin/roles", "Super admin role cannot be deleted."
            )
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
            HTMLResponse with the users table inside the admin shell.
        """
        denied = await self._require(request, "users.list")
        if denied is not None:
            return denied
        users = await self._user_store.list_users() if self._user_store else []
        html = render_users_list_page(
            users,
            error=str(request.query_params.get("error", "")),
            notice=str(request.query_params.get("notice", "")),
            super_admin_role=self._super_admin_role,
        )
        return await self.render_admin(
            request,
            html,
            title="Users",
            breadcrumbs=self.generate_breadcrumbs(
                ("Home", "/admin/"),
                current="Users",
            ),
        )

    # ------------------------------------------------------------------
    # GET/POST /users/{user_id}/roles — user role assignment
    # ------------------------------------------------------------------

    @get("/users/{user_id}/roles")
    async def user_roles_form(self, request: Request) -> HTMLResponse:
        """Render the user role assignment form.

        Args:
            request: Incoming HTTP request (user id in path).

        Returns:
            HTMLResponse with role checkboxes inside the admin shell.
        """
        denied = await self._require(request, "users.update")
        if denied is not None:
            return denied
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
        return await self.render_admin(
            request,
            html,
            title="User Roles",
            breadcrumbs=self.generate_breadcrumbs(
                ("Home", "/admin/"),
                ("Users", "/admin/users"),
                current=getattr(user, "name", None) or user_id,
            ),
        )

    @post("/users/{user_id}/roles")
    async def user_roles_submit(self, request: Request) -> Response:
        """Assign roles to a user (persisted via ``update_user``).

        Args:
            request: Incoming HTTP request (user id in path + roles).

        Returns:
            RedirectResponse with ``notice`` or ``error`` flash.
        """
        denied = await self._require(request, "users.update")
        if denied is not None:
            return denied
        form = await request.form()
        if not self._csrf_ok(request, str(form.get("csrf_token", ""))):
            return self._error_redirect(
                "/admin/users", "Invalid or expired security token. Please try again."
            )
        user_id = str(request.path_params.get("user_id", ""))
        roles = sorted({str(v) for v in form.getlist("roles")})
        if self._user_store is not None:
            users = await self._user_store.list_users()
            user = next(
                (u for u in users if getattr(u, "user_id", None) == user_id), None
            )
            if user is None:
                return self._error_redirect("/admin/users", "User not found.")
            user.roles = roles
            await self._user_store.update_user(user)
        return RedirectResponse(
            url="/admin/users?notice=User roles updated.", status_code=302
        )

    # ------------------------------------------------------------------
    # GET/POST /users/{user_id}/permissions — direct permission editing
    # ------------------------------------------------------------------

    @get("/users/{user_id}/permissions")
    async def user_permissions_form(self, request: Request) -> HTMLResponse:
        """Render the user direct-permission editing form.

        Args:
            request: Incoming HTTP request (user id in path).

        Returns:
            HTMLResponse with grouped permission checkboxes inside the shell.
        """
        denied = await self._require(request, "users.update")
        if denied is not None:
            return denied
        user = None
        user_id = str(request.path_params.get("user_id", ""))
        if self._user_store is not None:
            users = await self._user_store.list_users()
            user = next(
                (u for u in users if str(getattr(u, "user_id", "")) == user_id),
                None,
            )
        csrf_token = self._get_csrf_token(request)
        html = render_user_permissions_page(
            user,
            permission_options=self._inventory.options(),
            selected=set(getattr(user, "permissions", []) if user else []),
            error=str(request.query_params.get("error", "")),
            csrf_token=csrf_token,
        )
        return await self.render_admin(
            request,
            html,
            title="User Permissions",
            breadcrumbs=self.generate_breadcrumbs(
                ("Home", "/admin/"),
                ("Users", "/admin/users"),
                current=getattr(user, "name", None) or user_id,
            ),
        )

    @post("/users/{user_id}/permissions")
    async def user_permissions_submit(self, request: Request) -> Response:
        """Persist direct user permissions via ``update_user``.

        Args:
            request: Incoming HTTP request (user id in path + permissions).

        Returns:
            RedirectResponse with ``notice`` or ``error`` flash.
        """
        denied = await self._require(request, "users.update")
        if denied is not None:
            return denied
        form = await request.form()
        if not self._csrf_ok(request, str(form.get("csrf_token", ""))):
            return self._error_redirect(
                "/admin/users", "Invalid or expired security token. Please try again."
            )
        user_id = str(request.path_params.get("user_id", ""))
        permissions = self._collect_permissions(form)
        if self._user_store is not None:
            users = await self._user_store.list_users()
            user = next(
                (u for u in users if str(getattr(u, "user_id", "")) == user_id),
                None,
            )
            if user is None:
                return self._error_redirect("/admin/users", "User not found.")
            user.permissions = permissions
            await self._user_store.update_user(user)
        return RedirectResponse(
            url="/admin/users?notice=User permissions updated.", status_code=302
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _require(self, request: Request, permission: str) -> HTMLResponse | None:
        """Return a 403 page when the requesting user lacks the permission.

        Super-admin bypasses the check so bootstrap accounts with an empty
        permission set can still manage roles and users.

        Args:
            request: Incoming HTTP request (auth middleware populates
                ``request.state.user``).
            permission: Required ``resource.action`` permission string.

        Returns:
            ``None`` when access is granted, otherwise a 403 HTMLResponse
            rendered inside the admin shell.
        """
        user = getattr(request.state, "user", None)
        if user is None:
            return await self._forbidden(request, permission)
        roles = getattr(user, "roles", None) or ()
        permissions = getattr(user, "permissions", None) or ()
        if self._super_admin_role in roles or permission in permissions:
            return None
        return await self._forbidden(request, permission)

    async def _forbidden(self, request: Request, permission: str) -> HTMLResponse:
        """Render a 403 page inside the admin shell.

        Args:
            request: Incoming HTTP request.
            permission: Permission whose absence caused the denial.

        Returns:
            HTMLResponse with status 403.
        """
        response = await self.render_admin(
            request,
            f"<p>You do not have permission to access this page "
            f"(required: <code>{escape(permission)}</code>).</p>",
            title="Forbidden",
            breadcrumbs=self.generate_breadcrumbs(
                ("Home", "/admin/"),
                current="Forbidden",
            ),
        )
        response.status_code = 403
        return response

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
    def _error_redirect(url: str, message: str) -> Response:
        """Return a 302 redirect carrying an error flash message."""
        return RedirectResponse(
            url=f"{url}?error={quote_plus(message)}",
            status_code=302,
        )


__all__ = ["RbacController"]
