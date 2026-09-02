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
from lexigram.admin.rbac.effective import resolve_effective_permissions
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


def _fmt_ts(value: Any) -> str:
    """Best-effort compact timestamp rendering for table cells."""
    if value is None:
        return "—"
    text = str(value)
    return text.split(".", maxsplit=1)[0].replace("T", " ")


def _short_id(value: Any, length: int = 8) -> str:
    """Truncate an identifier for display — never render full tokens."""
    text = str(value or "")
    return f"{text[:length]}…" if len(text) > length else text


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

    @staticmethod
    def _effective_html(role_name: str, all_roles: list[Any]) -> str:
        """Read-only effective-permissions card for the edit page (R40).

        Mirrors runtime authorizer semantics via
        ``resolve_effective_permissions`` — cycle-safe, missing parents
        grant nothing but are surfaced as a warning.
        """
        eff = resolve_effective_permissions(
            role_name, {r.name: r for r in all_roles}
        )
        chip = (
            '<span class="inline-block font-mono text-xs rounded border '
            'border-border px-1.5 py-0.5 mr-1 mb-1">{}</span>'
        )
        direct_html = (
            "".join(chip.format(escape(p)) for p in sorted(eff.direct))
            or '<span class="text-sm text-muted-foreground">none</span>'
        )
        inherited_html = (
            "".join(
                '<span class="inline-block mr-2 mb-1">'
                + chip.format(escape(p))
                + '<span class="text-xs text-muted-foreground">via '
                + escape(", ".join(sources))
                + "</span></span>"
                for p, sources in eff.inherited.items()
            )
            or '<span class="text-sm text-muted-foreground">none</span>'
        )
        warning = ""
        if eff.missing:
            warning = (
                '<p class="text-sm text-amber-600 mt-3">Warning: this role '
                f"inherits {escape(', '.join(repr(m) for m in eff.missing))} "
                "which no longer exist"
                + ("s" if len(eff.missing) == 1 else "")
                + " — dangling entries grant nothing. Edit the role to "
                "remove them.</p>"
            )
        ancestors = (
            escape(", ".join(eff.ancestors)) if eff.ancestors else "none"
        )
        return (
            '<div class="bg-card border border-border rounded-xl p-6 mt-6 '
            'max-w-5xl" data-testid="effective-permissions">'
            '<h2 class="text-sm font-medium">Effective permissions '
            f'<span class="text-muted-foreground">({len(eff.all_permissions)}'
            " total)</span></h2>"
            '<p class="text-xs text-muted-foreground mt-1">What this role '
            "grants at runtime, including inheritance. Reflects the saved "
            "state — save changes to refresh.</p>"
            f'<h3 class="text-xs font-medium text-muted-foreground mt-4 mb-2">'
            f"Direct ({len(eff.direct)})</h3><div>{direct_html}</div>"
            f'<h3 class="text-xs font-medium text-muted-foreground mt-4 mb-2">'
            f"Inherited ({len(eff.inherited)}) — resolved chain: {ancestors}"
            f"</h3><div>{inherited_html}</div>"
            f"{warning}</div>"
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
        roles_by_name = {r.name: r for r in roles}
        rows = []
        for role in roles:
            edit_url = f"{base}/{quote_plus(role.name)}/edit"
            duplicate_url = f"{base}/new?from={quote_plus(role.name)}"
            eff = resolve_effective_permissions(role.name, roles_by_name)
            perm_count = str(len(role.permissions))
            if eff.inherited:
                perm_count += (
                    f' <span class="text-xs text-muted-foreground">'
                    f"(+{len(eff.inherited)} inherited)</span>"
                )
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
                f'<td class="px-4 py-3 text-sm">{perm_count}</td>'
                f'<td class="px-4 py-3 text-sm">{escape(", ".join(role.inherits) or "—")}</td>'
                f'<td class="px-4 py-3 text-sm">{held.get(role.name, 0)}</td>'
                f'<td class="px-4 py-3 text-sm"><a href="{escape(edit_url)}" '
                'class="font-medium text-primary hover:underline">Edit</a> '
                f'<a href="{escape(duplicate_url)}" '
                'class="font-medium text-primary hover:underline">Duplicate</a> '
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
        """Role creation form, optionally prefilled from ``?from=<role>``.

        Duplication reuses this form + the create POST (same CSRF,
        validation, duplicate-name rejection, audit) instead of a
        second mutation path (R40, doc 36 §2.4).
        """
        denied = self._guard(request)
        if denied is not None:
            return denied
        base = self._admin_path(request, "/admin/roles")
        name = ""
        description = ""
        permissions: set[str] = set()
        inherits: set[str] = set()
        source_note = ""
        source_name = str(request.query_params.get("from", "") or "").strip()
        if source_name:
            roles = (
                await self._role_service.list_roles() if self._role_service else []
            )
            source = next((r for r in roles if r.name == source_name), None)
            if source is None:
                return self._redirect(
                    base, f"Role '{source_name}' does not exist.", True
                )
            name = f"{source.name}-copy"[:64]
            description = source.description
            permissions = set(source.permissions)
            inherits = set(source.inherits)
            source_note = (
                '<p class="text-sm text-muted-foreground mb-4">'
                f"Duplicating <strong>{escape(source.name)}</strong> — "
                "permissions and inheritance are prefilled; adjust the name "
                "and save to create the copy.</p>"
            )
        html = source_note + await self._role_form(
            request,
            action_url=self._admin_path(request, "/admin/roles/create"),
            name=name,
            description=description,
            permissions=permissions,
            inherits=inherits,
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
        html += self._effective_html(role.name, roles)
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
        # Block deletion while other roles inherit this one (R40, doc 36
        # §2.5): the runtime treats a missing parent as permission-less,
        # so deleting would silently narrow the inheritors' effective
        # permissions.
        inheritors = sorted(
            r.name
            for r in await self._role_service.list_roles()
            if role_name in (r.inherits or [])
        )
        if inheritors:
            return self._redirect(
                base,
                f"Cannot delete '{role_name}': still inherited by "
                f"{', '.join(inheritors)}. Remove the inheritance first.",
                True,
            )
        result = await self._role_service.delete_role(
            role_name, actor_id=self._actor_id(request)
        )
        if result.is_err():
            return self._redirect(base, str(result.unwrap_err()), True)
        return self._redirect(base, f"Role '{role_name}' deleted.")


class UsersController(_AccessControlController):
    """Admin user lifecycle: listing, roles, create, deactivate (superadmin-only).

    Routes:
        GET  /admin/users                     - Admin list
        GET  /admin/users/new                 - Create form
        POST /admin/users/create              - Create (policy + duplicate guard)
        GET  /admin/users/{id}/edit           - Role assignment form
        POST /admin/users/{id}/update         - Save roles (last-superadmin guard)
        POST /admin/users/{id}/deactivate     - Deactivate (self + last-superadmin guards)
        POST /admin/users/{id}/activate       - Reactivate
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
        # Wired best-effort at mount time (di/mount/controllers.py):
        self._password_policy: Any = None  # AdminPasswordPolicyService
        self._session_service: Any = None  # AdminSessionServiceProtocol

    # -- helpers ------------------------------------------------------------

    def _policy_service(self) -> Any:
        """Wired password-policy service, or the default rule set.

        Creation must never run unvalidated: when mount-time wiring did
        not attach a service, fall back to the same default admin rule
        set the setup flow uses.
        """
        if self._password_policy is not None:
            return self._password_policy
        from lexigram.admin.auth.services.password_policy_service import (
            AdminPasswordPolicyService,
        )

        self._password_policy = AdminPasswordPolicyService()
        return self._password_policy

    def _deactivation_blocked(self, target: Any, all_users: list[Any]) -> bool:
        """True when deactivating *target* would leave zero active superadmins.

        Unlike role demotion, deactivation removes permanent-flag holders
        from the active pool too, so the guard applies to any superadmin
        standing. Fail-closed: with an empty/unreadable user listing the
        deactivation is blocked, because remaining superadmin standing
        cannot be proven.
        """
        if not self._holds_super(target):
            return False  # not a superadmin — no pool impact
        target_id = str(_user_field(target, "user_id", "id"))
        others = [
            u
            for u in all_users
            if str(_user_field(u, "user_id", "id")) != target_id
            and _user_field(u, "is_active", default=True) in (True, 1)
            and self._holds_super(u)
        ]
        return not others

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
        csrf = self._csrf_token(request)

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
            if uid == me:
                lifecycle = ""  # never offer self-deactivation
            elif active:
                lifecycle = (
                    f'<form method="post" action="{escape(base)}/'
                    f'{quote_plus(uid)}/deactivate" class="inline" '
                    "onsubmit=\"return confirm('Deactivate this admin? "
                    "Their sessions are revoked and they can no longer "
                    "log in.')\">"
                    f'<input type="hidden" name="csrf_token" value="{escape(csrf)}">'
                    '<button type="submit" class="text-sm font-medium '
                    'text-destructive hover:underline">Deactivate</button>'
                    "</form>"
                )
            else:
                lifecycle = (
                    f'<form method="post" action="{escape(base)}/'
                    f'{quote_plus(uid)}/activate" class="inline">'
                    f'<input type="hidden" name="csrf_token" value="{escape(csrf)}">'
                    '<button type="submit" class="text-sm font-medium '
                    'text-primary hover:underline">Activate</button>'
                    "</form>"
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
                'hover:underline">Edit roles</a>'
                + (' <span class="text-muted-foreground">·</span> ' if lifecycle else "")
                + lifecycle
                + "</td>"
                "</tr>"
            )

        html = (
            '<div class="flex justify-end mb-4">'
            f'<a href="{escape(base)}/new" class="{_BTN_CLS}">New admin</a>'
            "</div>"
        ) + self._table(
            ["Name", "Email", "Roles", "Status", ""],
            rows,
            "No admin users found.",
        )
        return await self._page(request, html, "Users", "Users", "/admin/users")

    @get("/new")
    async def new_page(self, request: Request) -> Response:
        """Create-admin form: identity, password, role checkboxes."""
        denied = self._guard(request)
        if denied is not None:
            return denied
        base = self._admin_path(request, "/admin/users")
        options = await self._role_options(await self._list_users())

        boxes = "".join(
            '<label class="flex items-center gap-2 text-sm py-1">'
            f'<input type="checkbox" name="roles" value="{escape(n)}"> {escape(n)}'
            + (
                ' <span class="text-xs text-muted-foreground">'
                "(super admin — full control)</span>"
                if n == self._super_admin_role
                else ""
            )
            + "</label>"
            for n in options
        )
        field_cls = (
            "w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
        )
        html = (
            f'<form method="post" action="{escape(base)}/create" '
            'class="space-y-4 max-w-xl">'
            f'<input type="hidden" name="csrf_token" value="{escape(self._csrf_token(request))}">'
            '<div><label class="block text-sm font-medium mb-1" for="new-admin-name">Name</label>'
            f'<input id="new-admin-name" name="name" required class="{field_cls}"></div>'
            '<div><label class="block text-sm font-medium mb-1" for="new-admin-email">Email</label>'
            f'<input id="new-admin-email" name="email" type="email" required class="{field_cls}"></div>'
            '<div><label class="block text-sm font-medium mb-1" for="new-admin-password">Password</label>'
            f'<input id="new-admin-password" name="password" type="password" '
            f'required autocomplete="new-password" class="{field_cls}"></div>'
            '<div><label class="block text-sm font-medium mb-1" '
            'for="new-admin-password-confirm">Confirm password</label>'
            f'<input id="new-admin-password-confirm" name="password_confirm" '
            f'type="password" required autocomplete="new-password" class="{field_cls}"></div>'
            '<fieldset class="border border-border rounded-lg p-4">'
            '<legend class="px-1 text-sm font-medium">Roles</legend>'
            f"{boxes}"
            '<p class="text-xs text-muted-foreground mt-2">Optional — an '
            "admin without roles can log in but reaches nothing "
            "privileged until roles are assigned.</p>"
            "</fieldset>"
            '<p class="text-sm text-muted-foreground">The new admin will be '
            "asked to verify their email address on first login.</p>"
            f'<button type="submit" class="{_BTN_CLS}">Create admin</button>'
            "</form>"
        )
        return await self._page(
            request, html, "New admin — Users", "Users", "/admin/users", "New admin"
        )

    @post("/create")
    async def create(self, request: Request) -> Response:
        """Create an admin account (CSRF + policy + duplicate guard, audited)."""
        denied = self._guard(request)
        if denied is not None:
            return denied
        base = self._admin_path(request, "/admin/users")
        form_url = f"{base}/new"
        form = await self._form(request)
        if not self._csrf_ok(request, str(form.get("csrf_token", ""))):
            return self._redirect(form_url, "Invalid or expired form token.", True)
        if self._user_store is None:
            return self._redirect(base, "User store unavailable.", True)

        name = str(form.get("name", "")).strip()
        email = str(form.get("email", "")).strip().lower()
        password = str(form.get("password", ""))
        confirm = str(form.get("password_confirm", ""))
        if not name or not email or "@" not in email:
            return self._redirect(form_url, "Name and a valid email are required.", True)
        if not password:
            return self._redirect(form_url, "Password is required.", True)
        if password != confirm:
            return self._redirect(form_url, "Passwords do not match.", True)

        policy_result = self._policy_service().validate(password, email=email)
        if not policy_result.is_valid:
            summary = "; ".join(v.message for v in policy_result.violations)
            return self._redirect(form_url, f"Password rejected: {summary}", True)

        # Load-bearing pre-check: the store's create_user silently resolves
        # to the existing user on duplicate email instead of failing, which
        # would make this "create" quietly report success (doc 34).
        try:
            existing = await self._user_store.get_user_by_email(email)
        except Exception:  # noqa: BLE001 — fail closed on unreadable store
            logger.warning("access_control.duplicate_check_failed", email=email)
            return self._redirect(form_url, "Could not verify email uniqueness.", True)
        if existing is not None:
            return self._redirect(
                form_url, "An admin with that email already exists.", True
            )

        getlist = getattr(form, "getlist", None)
        roles = sorted(
            {
                str(v).strip()
                for v in (getlist("roles") if getlist else [form.get("roles")])
                if v and str(v).strip()
            }
        )

        from lexigram.admin.lib.password import hash_password

        try:
            created = await self._user_store.create_user(
                name=name,
                email=email,
                hashed_password=hash_password(password),
                roles=roles,
            )
        except Exception:  # noqa: BLE001 — surface a friendly error, log the rest
            logger.exception("access_control.user_create_failed")
            return self._redirect(form_url, "Could not create the admin account.", True)

        await self._audit(
            request,
            AdminSecurityEventType.USER_CREATED,
            True,
            user_id=str(_user_field(created, "user_id", "id") or ""),
            email=email,
            roles=", ".join(roles),
        )
        logger.info("access_control.user_created", email=email, roles=roles)
        return self._redirect(base, f"Admin '{email}' created.")

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
        html += await self._sessions_html(request, user_id)
        return await self._page(
            request, html, f"{email} — Users", "Users", "/admin/users", email or user_id
        )

    # -- session panel (R42 — docs/09-01-2026/38-user-session-panel.md) -----

    async def _sessions_html(self, request: Request, user_id: str) -> str:
        """Active-session card for one admin, with revoke actions.

        Duck-typed against ``list_user_sessions`` so services predating
        the method degrade to a note; listing errors keep the roles form
        usable. The acting admin's own current session is never
        revocable from here (use Logout), matching the Security Center.
        """
        if self._session_service is None:
            return ""
        heading = (
            '<h2 class="text-sm font-medium text-foreground mt-8 mb-3">'
            "Active sessions</h2>"
        )
        lister = getattr(self._session_service, "list_user_sessions", None)
        if not callable(lister):
            return heading + (
                '<div class="bg-card border border-border rounded-xl p-5 '
                'text-sm text-muted-foreground">Per-user listing is not '
                "supported by the configured session service.</div>"
            )
        try:
            sessions = await lister(user_id, limit=50)
        except Exception:  # noqa: BLE001 — the roles form must keep working
            logger.warning("access_control.session_listing_failed", user_id=user_id)
            return heading + (
                '<div class="bg-card border border-border rounded-xl p-5 '
                'text-sm text-muted-foreground">Could not load sessions — '
                "check the server log.</div>"
            )

        base = self._admin_path(request, "/admin/users")
        csrf = self._csrf_token(request)
        actor = self.current_user(request)
        is_self = str(getattr(actor, "user_id", "")) == str(user_id)
        current_session_id = str(request.session.get("session_id", ""))

        rows = []
        for s in sessions:
            sid = str(s.get("session_id", ""))
            is_current = is_self and sid == current_session_id
            action = (
                '<span class="text-xs text-muted-foreground">this session</span>'
                if is_current
                else (
                    f'<form method="post" action="{escape(base)}/'
                    f'{quote_plus(user_id)}/sessions/revoke" class="inline">'
                    f'<input type="hidden" name="csrf_token" value="{escape(csrf)}">'
                    f'<input type="hidden" name="session_id" value="{escape(sid)}">'
                    '<button type="submit" class="text-sm font-medium '
                    'text-destructive hover:underline">Revoke</button></form>'
                )
            )
            rows.append(
                "<tr>"
                f'<td class="px-4 py-3 text-sm font-mono">{escape(_short_id(sid))}</td>'
                f'<td class="px-4 py-3 text-sm">{escape(str(s.get("ip_address") or "—"))}</td>'
                f'<td class="px-4 py-3 text-sm text-muted-foreground max-w-[16rem] '
                f'truncate">{escape(str(s.get("user_agent") or "—"))}</td>'
                f'<td class="px-4 py-3 text-sm">{escape(_fmt_ts(s.get("last_active_at")))}</td>'
                f'<td class="px-4 py-3 text-sm">{escape(_fmt_ts(s.get("expires_at")))}</td>'
                f'<td class="px-4 py-3 text-sm">{action}</td>'
                "</tr>"
            )

        revoke_all = ""
        if rows and not is_self:
            revoke_all = (
                f'<form method="post" action="{escape(base)}/'
                f'{quote_plus(user_id)}/sessions/revoke-all" class="mt-3">'
                f'<input type="hidden" name="csrf_token" value="{escape(csrf)}">'
                '<button type="submit" class="rounded-lg border border-destructive '
                'text-destructive px-4 py-2 text-sm font-medium">'
                "Sign out everywhere</button></form>"
            )
        elif rows and is_self:
            revoke_all = (
                '<p class="text-xs text-muted-foreground mt-3">Use Logout to '
                "end your own session; other sessions can be revoked "
                "individually.</p>"
            )
        return (
            heading
            + self._table(
                ["Session", "IP", "User agent", "Last active", "Expires", ""],
                rows,
                "No active sessions.",
            )
            + revoke_all
        )

    @post("/{user_id:str}/sessions/revoke")
    async def revoke_session(self, request: Request, user_id: str) -> Response:
        """Revoke ONE of the target user's sessions (CSRF, audited).

        The submitted session id must belong to the target user — the
        endpoint cannot be replayed with an arbitrary id from another
        account (doc 38 §2.3).
        """
        denied = self._guard(request)
        if denied is not None:
            return denied
        base = self._admin_path(request, "/admin/users")
        back = f"{base}/{quote_plus(user_id)}/edit"
        form = await self._form(request)
        if not self._csrf_ok(request, str(form.get("csrf_token", ""))):
            return self._redirect(back, "Invalid or expired form token.", True)
        if self._session_service is None:
            return self._redirect(back, "Session service unavailable.", True)

        session_id = str(form.get("session_id", "")).strip()
        if not session_id:
            return self._redirect(back, "Missing session id.", True)
        if session_id == str(request.session.get("session_id", "")):
            return self._redirect(back, "Use Logout to end your own session.", True)

        lister = getattr(self._session_service, "list_user_sessions", None)
        owned = (
            {str(s.get("session_id", "")) for s in await lister(user_id, limit=50)}
            if callable(lister)
            else set()
        )
        if session_id not in owned:
            return self._redirect(
                back, "That session does not belong to this user.", True
            )

        try:
            await self._session_service.revoke_session(session_id)
        except Exception:  # noqa: BLE001 — surface a friendly error, log the rest
            logger.exception("access_control.session_revoke_failed")
            return self._redirect(back, "Could not revoke the session.", True)

        await self._audit(
            request,
            AdminSecurityEventType.SESSION_REVOKED,
            True,
            user_id=user_id,
            revoked_session_id=_short_id(session_id),
            scope="single",
            source="user_form",
        )
        logger.info(
            "access_control.session_revoked",
            user_id=user_id,
            session_id=_short_id(session_id),
        )
        return self._redirect(back, "Session revoked.")

    @post("/{user_id:str}/sessions/revoke-all")
    async def revoke_all_sessions(self, request: Request, user_id: str) -> Response:
        """Sign the target user out everywhere (CSRF, audited).

        Blocked for the acting admin's own account — killing your own
        session mid-request is a logout, not an admin action.
        """
        denied = self._guard(request)
        if denied is not None:
            return denied
        base = self._admin_path(request, "/admin/users")
        back = f"{base}/{quote_plus(user_id)}/edit"
        form = await self._form(request)
        if not self._csrf_ok(request, str(form.get("csrf_token", ""))):
            return self._redirect(back, "Invalid or expired form token.", True)
        if self._session_service is None:
            return self._redirect(back, "Session service unavailable.", True)

        actor = self.current_user(request)
        if str(getattr(actor, "user_id", "")) == str(user_id):
            return self._redirect(
                back,
                "Use Logout to end your own session; other sessions can be "
                "revoked individually.",
                True,
            )

        try:
            await self._session_service.revoke_all_user_sessions(user_id)
        except Exception:  # noqa: BLE001 — surface a friendly error, log the rest
            logger.exception("access_control.session_revoke_all_failed")
            return self._redirect(back, "Could not revoke the sessions.", True)

        await self._audit(
            request,
            AdminSecurityEventType.SESSION_REVOKED,
            True,
            user_id=user_id,
            scope="all",
            source="user_form",
        )
        logger.info("access_control.sessions_revoked_all", user_id=user_id)
        return self._redirect(back, "All sessions revoked.")

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

    @post("/{user_id:str}/deactivate")
    async def deactivate(self, request: Request, user_id: str) -> Response:
        """Deactivate an admin (self + last-superadmin guards, audited).

        Sessions are revoked best-effort; even if revocation fails,
        ``authenticate()`` rejects inactive accounts so no new logins
        are possible.
        """
        denied = self._guard(request)
        if denied is not None:
            return denied
        base = self._admin_path(request, "/admin/users")
        form = await self._form(request)
        if not self._csrf_ok(request, str(form.get("csrf_token", ""))):
            return self._redirect(base, "Invalid or expired form token.", True)
        if self._user_store is None:
            return self._redirect(base, "User store unavailable.", True)

        me = str(getattr(self.current_user(request), "user_id", "") or "")
        if me and me == user_id:
            return self._redirect(
                base, "You cannot deactivate your own account.", True
            )

        target = await self._get_user(user_id)
        if target is None:
            return self._redirect(base, "Admin user not found.", True)
        email = str(_user_field(target, "email", default="") or "")
        if _user_field(target, "is_active", default=True) not in (True, 1):
            return self._redirect(base, f"'{email}' is already inactive.")

        if self._deactivation_blocked(target, await self._list_users()):
            return self._redirect(
                base, "Cannot deactivate the last active super admin.", True
            )

        try:
            target.is_active = False
            await self._user_store.update_user(target)
        except Exception:  # noqa: BLE001 — surface a friendly error, log the rest
            logger.exception("access_control.user_deactivate_failed")
            return self._redirect(base, "Could not deactivate the account.", True)

        if self._session_service is not None:
            try:
                await self._session_service.revoke_all_user_sessions(user_id)
            except Exception:  # noqa: BLE001 — inactive accounts cannot re-auth
                logger.warning(
                    "access_control.session_revocation_failed", user_id=user_id
                )

        await self._audit(
            request,
            AdminSecurityEventType.USER_DEACTIVATED,
            True,
            user_id=user_id,
            email=email,
        )
        logger.info("access_control.user_deactivated", user_id=user_id, email=email)
        return self._redirect(base, f"Admin '{email}' deactivated.")

    @post("/{user_id:str}/activate")
    async def activate(self, request: Request, user_id: str) -> Response:
        """Reactivate a previously deactivated admin (CSRF, audited)."""
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
        email = str(_user_field(target, "email", default="") or "")
        if _user_field(target, "is_active", default=True) in (True, 1):
            return self._redirect(base, f"'{email}' is already active.")

        try:
            target.is_active = True
            await self._user_store.update_user(target)
        except Exception:  # noqa: BLE001 — surface a friendly error, log the rest
            logger.exception("access_control.user_activate_failed")
            return self._redirect(base, "Could not reactivate the account.", True)

        await self._audit(
            request,
            AdminSecurityEventType.USER_REACTIVATED,
            True,
            user_id=user_id,
            email=email,
        )
        logger.info("access_control.user_reactivated", user_id=user_id, email=email)
        return self._redirect(base, f"Admin '{email}' reactivated.")
