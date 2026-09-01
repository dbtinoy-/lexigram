"""Access-control UI: role management and user role assignment (R10).

Two superadmin-only controllers over the existing RBAC backend
(``AdminRoleService``, ``PermissionInventoryService``, the admin user
store). Design: docs/09-01-2026/06-access-control-ui.md. Patterns
(gate, CSRF, flash, mount-time wiring) follow the Security Center
(docs/09-01-2026/05-security-center.md).
"""

from __future__ import annotations

from html import escape
import re
from secrets import token_hex
from typing import Any
from urllib.parse import quote_plus

from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

from lexigram.admin.auth.next_url import build_login_redirect
from lexigram.admin.auth.protocols import AdminCsrfServiceProtocol
from lexigram.admin.auth.types import AdminSecurityEventType
from lexigram.admin.controllers.base import AdminController
from lexigram.admin.engine.renderer import AdminRenderer
from lexigram.admin.rbac.inventory import PermissionInventoryService
from lexigram.admin.rbac.protocols import AdminRoleServiceProtocol
from lexigram.contracts.web import get, post
from lexigram.logging import get_logger

logger = get_logger(__name__)

__all__ = ["RolesController", "UsersController"]

#: ``resource.action`` with an optional ``:scope`` suffix (spec D2).
_PERMISSION_RE = re.compile(r"^[a-z0-9_-]+\.[a-z0-9_-]+(:(self|team|all))?$")
_ROLE_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")

_INPUT_CLS = "rounded-lg border border-border bg-background px-3 py-2 text-sm"
_BTN_CLS = (
    "rounded-lg bg-primary text-primary-foreground px-4 py-2 text-sm font-medium"
)


def _user_field(user: Any, *names: str, default: Any = "") -> Any:
    """Read the first present attribute/key from a user record."""
    for name in names:
        if isinstance(user, dict):
            if name in user:
                return user[name]
        elif hasattr(user, name):
            return getattr(user, name)
    return default


class _AccessControlController(AdminController):
    """Shared superadmin gate, CSRF, flash, and audit plumbing."""

    def __init__(
        self,
        renderer: AdminRenderer,
        csrf_service: AdminCsrfServiceProtocol | None = None,
        super_admin_role: str = "superadmin",
    ) -> None:
        """Initialise the shared access-control plumbing.

        Args:
            renderer: AdminRenderer for shell page rendering.
            csrf_service: CSRF token service (POST protection).
            super_admin_role: Configured super-admin role name.
        """
        super().__init__(renderer=renderer)
        self._csrf_service = csrf_service
        self._super_admin_role = super_admin_role
        # Wired best-effort at mount time (di/mount/controllers.py):
        self._user_store: Any = None  # AdminUserStoreProtocol
        self._audit_service: Any = None  # AdminAuditLogServiceProtocol

    # -- access control ---------------------------------------------------

    def _is_super_admin(self, user: Any) -> bool:
        """Literal superuser flag OR the configured super-admin role (B1)."""
        if getattr(user, "is_superuser", False) is True:
            return True
        from lexigram.admin.rbac.super_admin import is_super_admin

        return bool(
            self._super_admin_role and is_super_admin(user, self._super_admin_role)
        )

    def _guard(self, request: Request) -> Response | None:
        """Redirect anonymous users to login; 403 non-superadmins."""
        user = self.current_user(request)
        if not user or getattr(user, "user_id", "guest") == "guest":
            return RedirectResponse(
                url=build_login_redirect(
                    self._admin_path(request, "/admin/login"),
                    str(request.url.path),
                ),
                status_code=302,
            )
        if not self._is_super_admin(user):
            logger.info(
                "access_control.denied",
                user_id=str(getattr(user, "user_id", "unknown")),
                path=request.url.path,
            )
            raise HTTPException(status_code=403, detail="Super admin required")
        return None

    # -- helpers ------------------------------------------------------------

    def _actor_id(self, request: Request) -> str | None:
        """Acting admin user id for audit attribution, or ``None``."""
        user = self.current_user(request)
        return str(getattr(user, "user_id", "") or "") or None

    def _csrf_token(self, request: Request) -> str:
        """Return a CSRF token, creating and persisting the session id."""
        csrf_session_id = str(request.session.get("csrf_session_id", ""))
        if not csrf_session_id:
            csrf_session_id = token_hex(16)
            request.session["csrf_session_id"] = csrf_session_id
        if self._csrf_service is None:
            return ""
        return self._csrf_service.generate_token(csrf_session_id)

    def _csrf_ok(self, request: Request, csrf_token: str) -> bool:
        """Validate the submitted CSRF token against the session id."""
        if self._csrf_service is None:
            return True
        csrf_session_id = str(request.session.get("csrf_session_id", ""))
        return bool(
            csrf_session_id
            and self._csrf_service.validate_token(csrf_session_id, csrf_token)
        )

    @staticmethod
    def _redirect(url: str, message: str, is_error: bool = False) -> Response:
        """Return a 302 redirect carrying an error or notice flash param."""
        key = "error" if is_error else "notice"
        sep = "&" if "?" in url else "?"
        return RedirectResponse(
            url=f"{url}{sep}{key}={quote_plus(message)}", status_code=302
        )

    @staticmethod
    async def _form(request: Request) -> Any:
        """Return the request form, preferring the CSRF middleware's cache.

        The CSRF middleware consumes the body to validate the token; a bare
        ``request.form()`` on a fresh Request object would hang (doc 05).
        """
        return request.scope.get("admin_form_data") or await request.form()

    async def _audit(
        self,
        request: Request,
        event_type: AdminSecurityEventType,
        success: bool,
        **metadata: Any,
    ) -> None:
        """Append a security audit event attributed to the acting admin."""
        if self._audit_service is None:
            logger.warning(
                "access_control.audit_skipped_no_service",
                event_type=event_type.value,
            )
            return
        try:
            client = getattr(request, "client", None)
            user = self.current_user(request)
            await self._audit_service.log_event(
                event_type=event_type,
                ip_address=getattr(client, "host", "unknown"),
                user_agent=request.headers.get("user-agent", "") or "",
                success=success,
                admin_user_id=str(getattr(user, "user_id", "") or "") or None,
                metadata=metadata,
            )
        except Exception:  # noqa: BLE001 — audit failures must not break requests
            logger.warning("access_control.audit_failed", event_type=event_type.value)

    def _flash_from_query(self, request: Request, ctx: Any) -> None:
        """Surface ?notice=/?error= redirect params as flash messages."""
        error = request.query_params.get("error", "")
        notice = request.query_params.get("notice", "")
        if error:
            ctx.add_flash(error, "error")
        if notice:
            ctx.add_flash(notice, "success")

    async def _page(
        self,
        request: Request,
        html: str,
        title: str,
        section: str,
        section_path: str,
        crumb: str | None = None,
    ) -> Response:
        """Render *html* in the admin shell with section breadcrumbs."""
        from lexigram.admin.state.context import AdminContextManager

        async with AdminContextManager(request) as ctx:
            self._flash_from_query(request, ctx)
            crumbs: list[tuple[str, str]] = [("Home", self._admin_path(request))]
            current = section
            if crumb:
                crumbs.append((section, self._admin_path(request, section_path)))
                current = crumb
            return await self.render_admin(
                request,
                html,
                title=title,
                breadcrumbs=self.generate_breadcrumbs(*crumbs, current=current),
            )

    @staticmethod
    def _table(headers: list[str], rows: list[str], empty: str) -> str:
        if not rows:
            return (
                '<div class="bg-card border border-border rounded-xl p-8 '
                'text-center text-muted-foreground">' + escape(empty) + "</div>"
            )
        head = "".join(
            '<th class="px-4 py-3 text-left text-xs font-medium '
            f'text-muted-foreground uppercase tracking-wider">{escape(h)}</th>'
            for h in headers
        )
        return (
            '<div class="bg-card border border-border rounded-xl overflow-x-auto">'
            '<table class="min-w-full divide-y divide-border">'
            f"<thead><tr>{head}</tr></thead>"
            '<tbody class="divide-y divide-border">' + "".join(rows) + "</tbody>"
            "</table></div>"
        )

    # -- shared user-record helpers ----------------------------------------

    async def _list_users(self) -> list[Any]:
        """All admin user records, or [] when the store is unavailable."""
        if self._user_store is None:
            return []
        try:
            return list(await self._user_store.list_users() or [])
        except Exception:  # noqa: BLE001 — page availability over completeness
            logger.warning("access_control.user_listing_failed")
            return []

    def _holds_super(self, user: Any) -> bool:
        """True when a user record carries superadmin standing."""
        if _user_field(user, "is_superuser", default=False) is True:
            return True
        roles = _user_field(user, "roles", default=None) or []
        return self._super_admin_role in roles


class RolesController(_AccessControlController):
    """Role management: list, create, edit, delete (superadmin-only).

    Routes:
        GET  /admin/roles               - Role list
        GET  /admin/roles/new           - Create form
        POST /admin/roles/create        - Create
        GET  /admin/roles/{name}/edit   - Edit form
        POST /admin/roles/{name}/update - Update
        POST /admin/roles/{name}/delete - Delete (blocked while assigned)
    """

    prefix = "/roles"

    def __init__(
        self,
        renderer: AdminRenderer,
        csrf_service: AdminCsrfServiceProtocol | None = None,
        role_service: AdminRoleServiceProtocol | None = None,
        permission_inventory: PermissionInventoryService | None = None,
        super_admin_role: str = "superadmin",
    ) -> None:
        """Initialise the roles controller.

        Args:
            renderer: AdminRenderer for shell page rendering.
            csrf_service: CSRF token service.
            role_service: Role CRUD orchestrator (mirrors + audits).
            permission_inventory: Per-resource permission options.
            super_admin_role: Configured super-admin role name.
        """
        super().__init__(
            renderer=renderer,
            csrf_service=csrf_service,
            super_admin_role=super_admin_role,
        )
        self._role_service = role_service
        self._inventory = permission_inventory

    # -- form parsing -------------------------------------------------------

    @staticmethod
    def _selected(form: Any, field: str) -> list[str]:
        """Multi-value form field as a list (FormData or plain dict)."""
        getlist = getattr(form, "getlist", None)
        if getlist is not None:
            return [str(v) for v in getlist(field)]
        value = form.get(field)
        if value is None:
            return []
        return [str(value)]

    @classmethod
    def _parse_permissions(cls, form: Any) -> tuple[list[str], list[str]]:
        """Collect matrix checkboxes + custom lines; validate format.

        Returns:
            ``(valid, rejected)`` permission string lists.
        """
        raw = cls._selected(form, "permissions")
        raw += [
            line.strip()
            for line in str(form.get("custom_permissions", "")).splitlines()
        ]
        valid: list[str] = []
        rejected: list[str] = []
        for entry in raw:
            entry = entry.strip().lower()
            if not entry:
                continue
            if _PERMISSION_RE.match(entry):
                valid.append(entry)
            else:
                rejected.append(entry)
        return sorted(set(valid)), rejected

    # -- rendering ----------------------------------------------------------

    def _matrix_html(self, checked: set[str]) -> str:
        """Grouped permission checkboxes from the live inventory."""
        options = self._inventory.options() if self._inventory else {}
        groups = []
        for resource, perms in options.items():
            boxes = "".join(
                '<label class="flex items-center gap-2 text-sm py-0.5">'
                f'<input type="checkbox" name="permissions" value="{escape(p)}"'
                + (" checked" if p in checked else "")
                + f'> <span class="font-mono text-xs">{escape(p)}</span></label>'
                for p in perms
            )
            groups.append(
                '<fieldset class="border border-border rounded-lg p-3">'
                f'<legend class="px-1 text-sm font-medium">{escape(resource)}</legend>'
                f"{boxes}</fieldset>"
            )
        known = {p for perms in options.values() for p in perms}
        custom = "\n".join(sorted(p for p in checked if p not in known))
        return (
            '<div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">'
            + "".join(groups)
            + "</div>"
            '<label class="block text-sm text-muted-foreground mt-4">'
            "Custom permissions (one per line, <code>resource.action</code>"
            " with optional <code>:self|:team|:all</code>)"
            f'<textarea name="custom_permissions" rows="3" class="{_INPUT_CLS} '
            f'block mt-1 w-full font-mono">{escape(custom)}</textarea></label>'
        )

    def _inherits_html(self, all_roles: list[Any], current: str, checked: set[str]) -> str:
        """Inheritance checkboxes over the other stored roles."""
        names = [r.name for r in all_roles if r.name != current]
        if not names:
            return ""
        boxes = "".join(
            '<label class="flex items-center gap-2 text-sm py-0.5">'
            f'<input type="checkbox" name="inherits" value="{escape(n)}"'
            + (" checked" if n in checked else "")
            + f"> {escape(n)}</label>"
            for n in names
        )
        return (
            '<fieldset class="border border-border rounded-lg p-3 mt-4">'
            '<legend class="px-1 text-sm font-medium">Inherits from</legend>'
            f"{boxes}</fieldset>"
        )

    async def _role_form(
        self,
        request: Request,
        *,
        action_url: str,
        name: str = "",
        description: str = "",
        permissions: set[str] | None = None,
        inherits: set[str] | None = None,
        name_locked: bool = False,
        submit_label: str = "Create role",
    ) -> str:
        """Render the shared create/edit role form."""
        roles = await self._role_service.list_roles() if self._role_service else []
        name_field = (
            f'<input type="text" value="{escape(name)}" disabled class="{_INPUT_CLS} '
            'block mt-1 w-full max-w-sm opacity-70">'
            f'<input type="hidden" name="name" value="{escape(name)}">'
            if name_locked
            else f'<input type="text" name="name" value="{escape(name)}" required '
            'pattern="[a-z0-9][a-z0-9_-]*" maxlength="64" '
            f'placeholder="content-editor" class="{_INPUT_CLS} block mt-1 w-full max-w-sm">'
        )
        return (
            f'<form method="post" action="{escape(action_url)}" class="space-y-4 max-w-5xl">'
            f'<input type="hidden" name="csrf_token" value="{escape(self._csrf_token(request))}">'
            f'<label class="block text-sm text-muted-foreground">Name{name_field}</label>'
            '<label class="block text-sm text-muted-foreground">Description'
            f'<input type="text" name="description" value="{escape(description)}" '
            f'maxlength="255" class="{_INPUT_CLS} block mt-1 w-full max-w-xl"></label>'
            + self._matrix_html(permissions or set())
            + self._inherits_html(roles, name, inherits or set())
            + f'<button type="submit" class="{_BTN_CLS}">{escape(submit_label)}</button>'
            "</form>"
        )

    # -- routes -------------------------------------------------------------

    @get("/")
    async def list_page(self, request: Request) -> Response:
        """Role list with per-role edit/delete actions."""
        denied = self._guard(request)
        if denied is not None:
            return denied
        roles = await self._role_service.list_roles() if self._role_service else []
        users = await self._list_users()
        held: dict[str, int] = {}
        for u in users:
            for r in _user_field(u, "roles", default=None) or []:
                held[str(r)] = held.get(str(r), 0) + 1

        base = self._admin_path(request, "/admin/roles")
        csrf = self._csrf_token(request)
        rows = []
        for role in roles:
            edit_url = f"{base}/{quote_plus(role.name)}/edit"
            badges = ""
            if role.is_system:
                badges += (
                    ' <span class="text-xs rounded-full border border-border '
                    'px-2 py-0.5 text-muted-foreground">system</span>'
                )
            in_use = held.get(role.name, 0)
            delete_html = (
                '<span class="text-xs text-muted-foreground">protected</span>'
                if role.is_system
                else (
                    f'<span class="text-xs text-muted-foreground">held by {in_use}</span>'
                    if in_use
                    else (
                        f'<form method="post" action="{escape(base)}/'
                        f'{quote_plus(role.name)}/delete" class="inline">'
                        f'<input type="hidden" name="csrf_token" value="{escape(csrf)}">'
                        '<button type="submit" class="text-sm font-medium '
                        'text-destructive hover:underline">Delete</button></form>'
                    )
                )
            )
            rows.append(
                "<tr>"
                f'<td class="px-4 py-3 text-sm font-medium">{escape(role.name)}{badges}</td>'
                f'<td class="px-4 py-3 text-sm text-muted-foreground">{escape(role.description or "—")}</td>'
                f'<td class="px-4 py-3 text-sm">{len(role.permissions)}</td>'
                f'<td class="px-4 py-3 text-sm">{escape(", ".join(role.inherits) or "—")}</td>'
                f'<td class="px-4 py-3 text-sm">{held.get(role.name, 0)}</td>'
                f'<td class="px-4 py-3 text-sm"><a href="{escape(edit_url)}" '
                'class="font-medium text-primary hover:underline">Edit</a> '
                f"{delete_html}</td>"
                "</tr>"
            )

        html = (
            '<div class="flex items-center justify-between mb-4">'
            '<p class="text-sm text-muted-foreground">Roles group permissions; '
            "assign them to admins on the Users page.</p>"
            f'<a href="{escape(base)}/new" class="{_BTN_CLS}">New role</a></div>'
            + self._table(
                ["Role", "Description", "Permissions", "Inherits", "Held by", ""],
                rows,
                "No roles defined yet — create the first one.",
            )
        )
        return await self._page(request, html, "Roles", "Roles", "/admin/roles")

    @get("/new")
    async def new_page(self, request: Request) -> Response:
        """Blank role creation form."""
        denied = self._guard(request)
        if denied is not None:
            return denied
        html = await self._role_form(
            request,
            action_url=self._admin_path(request, "/admin/roles/create"),
        )
        return await self._page(
            request, html, "New role — Roles", "Roles", "/admin/roles", "New role"
        )

    @post("/create")
    async def create(self, request: Request) -> Response:
        """Create a role from the form (CSRF-checked)."""
        denied = self._guard(request)
        if denied is not None:
            return denied
        base = self._admin_path(request, "/admin/roles")
        form = await self._form(request)
        if not self._csrf_ok(request, str(form.get("csrf_token", ""))):
            return self._redirect(base, "Invalid or expired form token.", True)
        if self._role_service is None:
            return self._redirect(base, "Role service unavailable.", True)

        name = str(form.get("name", "")).strip().lower()
        if not _ROLE_NAME_RE.match(name):
            return self._redirect(
                f"{base}/new",
                "Role names use lowercase letters, digits, '-' and '_'.",
                True,
            )
        permissions, rejected = self._parse_permissions(form)
        if rejected:
            return self._redirect(
                f"{base}/new",
                f"Invalid permission format: {', '.join(rejected[:3])}",
                True,
            )
        result = await self._role_service.create_role(
            name=name,
            description=str(form.get("description", "")),
            permissions=permissions,
            inherits=self._selected(form, "inherits"),
            actor_id=self._actor_id(request),
        )
        if result.is_err():
            return self._redirect(f"{base}/new", str(result.unwrap_err()), True)
        return self._redirect(base, f"Role '{name}' created.")

    @get("/{role_name:str}/edit")
    async def edit_page(self, request: Request, role_name: str) -> Response:
        """Prefilled edit form for one role."""
        denied = self._guard(request)
        if denied is not None:
            return denied
        base = self._admin_path(request, "/admin/roles")
        role = None
        if self._role_service is not None:
            roles = await self._role_service.list_roles()
            role = next((r for r in roles if r.name == role_name), None)
        if role is None:
            return self._redirect(base, f"Role '{role_name}' does not exist.", True)
        html = await self._role_form(
            request,
            action_url=f"{base}/{quote_plus(role.name)}/update",
            name=role.name,
            description=role.description,
            permissions=set(role.permissions),
            inherits=set(role.inherits),
            name_locked=True,
            submit_label="Save changes",
        )
        return await self._page(
            request,
            html,
            f"{role.name} — Roles",
            "Roles",
            "/admin/roles",
            role.name,
        )

    @post("/{role_name:str}/update")
    async def update(self, request: Request, role_name: str) -> Response:
        """Persist role edits (CSRF-checked)."""
        denied = self._guard(request)
        if denied is not None:
            return denied
        base = self._admin_path(request, "/admin/roles")
        form = await self._form(request)
        if not self._csrf_ok(request, str(form.get("csrf_token", ""))):
            return self._redirect(base, "Invalid or expired form token.", True)
        if self._role_service is None:
            return self._redirect(base, "Role service unavailable.", True)
        permissions, rejected = self._parse_permissions(form)
        if rejected:
            return self._redirect(
                f"{base}/{quote_plus(role_name)}/edit",
                f"Invalid permission format: {', '.join(rejected[:3])}",
                True,
            )
        result = await self._role_service.update_role(
            name=role_name,
            description=str(form.get("description", "")),
            permissions=permissions,
            inherits=self._selected(form, "inherits"),
            actor_id=self._actor_id(request),
        )
        if result.is_err():
            return self._redirect(base, str(result.unwrap_err()), True)
        return self._redirect(base, f"Role '{role_name}' updated.")

    @post("/{role_name:str}/delete")
    async def delete(self, request: Request, role_name: str) -> Response:
        """Delete a role unless it is a system role or still assigned."""
        denied = self._guard(request)
        if denied is not None:
            return denied
        base = self._admin_path(request, "/admin/roles")
        form = await self._form(request)
        if not self._csrf_ok(request, str(form.get("csrf_token", ""))):
            return self._redirect(base, "Invalid or expired form token.", True)
        if self._role_service is None:
            return self._redirect(base, "Role service unavailable.", True)

        holders = sum(
            1
            for u in await self._list_users()
            if role_name in (_user_field(u, "roles", default=None) or [])
        )
        if holders:
            return self._redirect(
                base,
                f"Cannot delete '{role_name}': still assigned to {holders} "
                f"admin{'s' if holders != 1 else ''}. Reassign them first.",
                True,
            )
        result = await self._role_service.delete_role(
            role_name, actor_id=self._actor_id(request)
        )
        if result.is_err():
            return self._redirect(base, str(result.unwrap_err()), True)
        return self._redirect(base, f"Role '{role_name}' deleted.")


class UsersController(_AccessControlController):
    """Admin user listing and role assignment (superadmin-only).

    Routes:
        GET  /admin/users                 - Admin list
        GET  /admin/users/{id}/edit       - Role assignment form
        POST /admin/users/{id}/update     - Save roles (last-superadmin guard)
    """

    prefix = "/users"

    def __init__(
        self,
        renderer: AdminRenderer,
        csrf_service: AdminCsrfServiceProtocol | None = None,
        role_service: AdminRoleServiceProtocol | None = None,
        super_admin_role: str = "superadmin",
    ) -> None:
        """Initialise the users controller.

        Args:
            renderer: AdminRenderer for shell page rendering.
            csrf_service: CSRF token service.
            role_service: Role service for assignment options.
            super_admin_role: Configured super-admin role name.
        """
        super().__init__(
            renderer=renderer,
            csrf_service=csrf_service,
            super_admin_role=super_admin_role,
        )
        self._role_service = role_service

    # -- helpers ------------------------------------------------------------

    async def _role_options(self, users: list[Any]) -> list[str]:
        """Stored roles ∪ roles held by any user ∪ the super-admin role.

        Keeps the setup-granted super-admin role editable even when it has
        no ``admin_roles`` row (doc 06).
        """
        names: set[str] = {self._super_admin_role} if self._super_admin_role else set()
        if self._role_service is not None:
            try:
                names.update(r.name for r in await self._role_service.list_roles())
            except Exception:  # noqa: BLE001 — degrade to held-role options
                logger.warning("access_control.role_listing_failed")
        for u in users:
            names.update(str(r) for r in _user_field(u, "roles", default=None) or [])
        return sorted(n for n in names if n)

    async def _get_user(self, user_id: str) -> Any | None:
        """Fetch one user record by id, or ``None``."""
        if self._user_store is None:
            return None
        try:
            return await self._user_store.get_user_by_id(user_id)
        except Exception:  # noqa: BLE001 — treated as not-found by callers
            logger.warning("access_control.user_lookup_failed")
            return None

    def _demotion_blocked(
        self, target: Any, new_roles: list[str], all_users: list[Any]
    ) -> bool:
        """True when saving *new_roles* would leave zero superadmins.

        Fail-closed: with an empty/unreadable user listing the demotion is
        blocked, because remaining superadmin standing cannot be proven.
        """
        if not self._holds_super(target):
            return False  # not a demotion
        if _user_field(target, "is_superuser", default=False) is True:
            return False  # flag survives role edits
        if self._super_admin_role in new_roles:
            return False  # keeps the role
        target_id = str(_user_field(target, "user_id", "id"))
        others = [
            u
            for u in all_users
            if str(_user_field(u, "user_id", "id")) != target_id
            and _user_field(u, "is_active", default=True) in (True, 1)
            and self._holds_super(u)
        ]
        return not others

    # -- routes -------------------------------------------------------------

    @get("/")
    async def list_page(self, request: Request) -> Response:
        """Admin user list with role chips and edit links."""
        denied = self._guard(request)
        if denied is not None:
            return denied
        users = await self._list_users()
        base = self._admin_path(request, "/admin/users")
        me = str(getattr(self.current_user(request), "user_id", ""))

        rows = []
        for u in users:
            uid = str(_user_field(u, "user_id", "id"))
            roles = [str(r) for r in _user_field(u, "roles", default=None) or []]
            chips = (
                " ".join(
                    '<span class="text-xs rounded-full border border-border '
                    f'px-2 py-0.5">{escape(r)}</span>'
                    for r in roles
                )
                or '<span class="text-muted-foreground">—</span>'
            )
            active = _user_field(u, "is_active", default=True) in (True, 1)
            status = (
                '<span class="text-xs font-medium text-green-600">active</span>'
                if active
                else '<span class="text-xs font-medium text-destructive">inactive</span>'
            )
            you = (
                ' <span class="text-xs text-primary font-medium">(you)</span>'
                if uid == me
                else ""
            )
            rows.append(
                "<tr>"
                f'<td class="px-4 py-3 text-sm font-medium">'
                f'{escape(str(_user_field(u, "name", default="") or "—"))}{you}</td>'
                f'<td class="px-4 py-3 text-sm">{escape(str(_user_field(u, "email", default="") or "—"))}</td>'
                f'<td class="px-4 py-3 text-sm">{chips}</td>'
                f'<td class="px-4 py-3 text-sm">{status}</td>'
                f'<td class="px-4 py-3 text-sm"><a href="{escape(base)}/'
                f'{quote_plus(uid)}/edit" class="font-medium text-primary '
                'hover:underline">Edit roles</a></td>'
                "</tr>"
            )

        html = self._table(
            ["Name", "Email", "Roles", "Status", ""],
            rows,
            "No admin users found.",
        )
        return await self._page(request, html, "Users", "Users", "/admin/users")

    @get("/{user_id:str}/edit")
    async def edit_page(self, request: Request, user_id: str) -> Response:
        """Role assignment checkboxes for one admin."""
        denied = self._guard(request)
        if denied is not None:
            return denied
        base = self._admin_path(request, "/admin/users")
        target = await self._get_user(user_id)
        if target is None:
            return self._redirect(base, "Admin user not found.", True)

        users = await self._list_users()
        options = await self._role_options(users)
        current = {str(r) for r in _user_field(target, "roles", default=None) or []}
        email = str(_user_field(target, "email", default="") or "")

        boxes = "".join(
            '<label class="flex items-center gap-2 text-sm py-1">'
            f'<input type="checkbox" name="roles" value="{escape(n)}"'
            + (" checked" if n in current else "")
            + f"> {escape(n)}"
            + (
                ' <span class="text-xs text-muted-foreground">(super admin)</span>'
                if n == self._super_admin_role
                else ""
            )
            + "</label>"
            for n in options
        )
        flag_note = (
            '<p class="text-sm text-muted-foreground mt-2">This account also '
            "carries the permanent superuser flag.</p>"
            if _user_field(target, "is_superuser", default=False) is True
            else ""
        )
        html = (
            f'<form method="post" action="{escape(base)}/{quote_plus(user_id)}/update" '
            'class="space-y-4 max-w-xl">'
            f'<input type="hidden" name="csrf_token" value="{escape(self._csrf_token(request))}">'
            '<fieldset class="border border-border rounded-lg p-4">'
            f'<legend class="px-1 text-sm font-medium">Roles for {escape(email)}</legend>'
            f"{boxes}</fieldset>{flag_note}"
            f'<button type="submit" class="{_BTN_CLS}">Save roles</button>'
            "</form>"
        )
        return await self._page(
            request, html, f"{email} — Users", "Users", "/admin/users", email or user_id
        )

    @post("/{user_id:str}/update")
    async def update(self, request: Request, user_id: str) -> Response:
        """Persist role assignment (CSRF + last-superadmin guard, audited)."""
        denied = self._guard(request)
        if denied is not None:
            return denied
        base = self._admin_path(request, "/admin/users")
        form = await self._form(request)
        if not self._csrf_ok(request, str(form.get("csrf_token", ""))):
            return self._redirect(base, "Invalid or expired form token.", True)
        if self._user_store is None:
            return self._redirect(base, "User store unavailable.", True)

        target = await self._get_user(user_id)
        if target is None:
            return self._redirect(base, "Admin user not found.", True)

        getlist = getattr(form, "getlist", None)
        new_roles = sorted(
            {
                str(v).strip()
                for v in (getlist("roles") if getlist else [form.get("roles")])
                if v and str(v).strip()
            }
        )
        users = await self._list_users()
        if self._demotion_blocked(target, new_roles, users):
            return self._redirect(
                f"{base}/{quote_plus(user_id)}/edit",
                "Cannot remove super-admin access from the last super admin.",
                True,
            )

        before = [str(r) for r in _user_field(target, "roles", default=None) or []]
        try:
            target.roles = new_roles
            await self._user_store.update_user(target)
        except Exception:  # noqa: BLE001 — surface a friendly error, log the rest
            logger.exception("access_control.role_assignment_failed")
            return self._redirect(base, "Could not save role changes.", True)

        await self._audit(
            request,
            AdminSecurityEventType.USER_ROLES_UPDATED,
            True,
            user_id=user_id,
            email=str(_user_field(target, "email", default="") or ""),
            roles_before=", ".join(before),
            roles_after=", ".join(new_roles),
        )
        logger.info(
            "access_control.user_roles_updated",
            user_id=user_id,
            roles_before=before,
            roles_after=new_roles,
        )
        return self._redirect(base, "Roles updated.")
