"""Plugins controller — list and toggle plugins via the plugin-state toolbox.

The page is a thin consumer of the passive ``lexigram-plugins`` primitives:
``discover_plugins()`` lists metadata-only descriptors, and
``load_disabled``/``update_disabled`` read and mutate the boot-file mirror
(``.lexigram/plugins.json`` by default) under an exclusive file lock.
Toggling applies on next boot — the mechanism stays passive; this
controller never instantiates plugins, only the admin-facing surface over
the same primitives an app would call.
"""

from __future__ import annotations

import secrets
from typing import TYPE_CHECKING, Any
from urllib.parse import quote_plus

from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

from lexigram.admin.config import AdminRbacConfig
from lexigram.admin.controllers.base import AdminController
from lexigram.admin.rbac.super_admin import is_super_admin
from lexigram.contracts.web import get, post
from lexigram.logging import get_logger
from lexigram.ui import el

if TYPE_CHECKING:
    from lexigram.admin.auth.protocols import (
        AdminAuditLogServiceProtocol,
        AdminCsrfServiceProtocol,
    )
    from lexigram.admin.engine.renderer import AdminRenderer
    from lexigram.contracts.plugins import PluginDescriptor

logger = get_logger(__name__)

__all__ = ["PluginsController"]

_REQUIRED_PERMISSIONS = frozenset({"admin.settings.edit"})


def _load_toolbox() -> tuple[Any, Any] | None:
    """Import the lexigram-plugins toolbox, returning None when absent.

    Returns:
        A ``(discovery, state)`` module pair, or ``None`` when the
        ``lexigram-plugins`` package is not installed.
    """
    try:
        from lexigram.plugins import discovery, state

        return (discovery, state)
    except ImportError:
        logger.debug("plugins.controller_toolbox_missing")
        return None


class PluginsController(AdminController):
    """Admin page listing discovered plugins with enable/disable toggles.

    Routes:
        GET  /admin/plugins           - Plugin listing
        POST /admin/plugins/toggle    - Toggle one plugin (disable/enable)
    """

    prefix = "/plugins"

    def __init__(
        self,
        renderer: AdminRenderer,
        csrf_service: AdminCsrfServiceProtocol | None = None,
        audit_service: AdminAuditLogServiceProtocol | None = None,
        rbac_config: AdminRbacConfig | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(renderer=renderer, **kwargs)
        self._csrf_service = csrf_service
        self._audit_service = audit_service
        self._rbac_config = rbac_config

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------

    @get("/")
    async def index(self, request: Request) -> Response:
        # Sec-2026-08-16-L5: no per-page permission on the read-only listing.
        # The global AdminAuthorizationMiddleware gates every non-public
        # request; this page exposes only entry-point metadata + the disabled
        # set; only POST /toggle requires superadmin / admin.settings.edit.
        # Accepted posture — see
        # docs/superpowers/specs/2026-08-16-security-plugins-design.md.
        """Render the plugin listing page."""
        toolbox = _load_toolbox()
        if toolbox is None:
            return await self.render_admin(
                request,
                self._render_empty("No plugin toolbox available."),
                title="Plugins",
                breadcrumbs=self.generate_breadcrumbs(
                    ("Home", "/admin/"),
                    current="Plugins",
                ),
            )
        discovery, state = toolbox

        descriptors = discovery.discover_plugins()
        disabled = state.load_disabled()
        if not descriptors:
            return await self.render_admin(
                request,
                self._render_empty("No plugins discovered."),
                title="Plugins",
                breadcrumbs=self.generate_breadcrumbs(
                    ("Home", "/admin/"),
                    current="Plugins",
                ),
            )

        content = self._render_list(request, descriptors, disabled)
        return await self.render_admin(
            request,
            content,
            title="Plugins",
            breadcrumbs=self.generate_breadcrumbs(
                ("Home", "/admin/"),
                current="Plugins",
            ),
        )

    @post("/toggle")
    async def toggle(self, request: Request) -> Response:
        """Toggle one plugin's enabled state (applies on next boot)."""
        form = request.scope.get("admin_form_data") or await request.form()
        csrf_token = str(form.get("csrf_token", ""))
        if not self._user_can_manage(request):
            await self._audit(request, success=False, reason="permission_denied")
            return self._error_redirect("/admin/plugins", "Permission denied.")
        if not self._csrf_ok(request, csrf_token):
            await self._audit(request, success=False, reason="csrf_failed")
            return self._error_redirect("/admin/plugins", "Invalid CSRF token.")

        plugin_name = str(form.get("plugin", "")).strip()
        toolbox = _load_toolbox()
        if toolbox is None:
            await self._audit(request, success=False, reason="toolbox_missing")
            return self._error_redirect("/admin/plugins", "Toolbox not available.")
        discovery, state = toolbox

        descriptors = discovery.discover_plugins()
        entry_points = {
            d.provider_entry_point
            for d in descriptors
            if self._is_known(d, plugin_name)
        }
        if not entry_points:
            await self._audit(request, success=False, reason="plugin_unknown")
            return self._error_redirect("/admin/plugins", "Unknown plugin.")

        disabled = state.load_disabled()
        action = "enabled" if entry_points <= disabled else "disabled"

        def flip(current: set[str]) -> set[str]:
            """Toggle ``entry_points`` out of (or into) ``current``."""
            if entry_points <= current:
                current.difference_update(entry_points)
            else:
                current.update(entry_points)
            return current

        from lexigram.plugins.exceptions import PluginStateError

        try:
            state.update_disabled(flip)
        except PluginStateError:
            await self._audit(request, success=False, reason="state_write_failed")
            return self._error_redirect(
                "/admin/plugins", "Could not save plugin state."
            )
        await self._audit(request, success=True, plugin=plugin_name, action=action)
        return RedirectResponse(
            url=f"/admin/plugins?notice={quote_plus(f'Plugin {action}.')}",
            status_code=302,
        )

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _render_empty(self, message: str) -> Any:
        return el(
            "div",
            el(
                "h1",
                "Plugins",
                class_="text-2xl font-bold text-foreground",
            ),
            el(
                "p",
                message,
                class_="text-muted-foreground mt-2",
            ),
            class_="p-6",
        )

    def _render_list(
        self,
        request: Request,
        descriptors: list[PluginDescriptor],
        disabled: set[str],
    ) -> Any:
        rows = [
            self._render_row(request, d, d.provider_entry_point in disabled)
            for d in descriptors
        ]
        return el(
            "div",
            el("h1", "Plugins", class_="text-2xl font-bold text-foreground"),
            el(
                "p",
                "Enable or disable installed plugins. Changes apply on next boot.",
                class_="text-muted-foreground mt-1",
            ),
            el(
                "div",
                *rows,
                class_="mt-6 divide-y divide-border border border-border rounded-xl",
            ),
            class_="p-6",
        )

    def _render_row(
        self,
        request: Request,
        descriptor: PluginDescriptor,
        is_disabled: bool,
    ) -> Any:
        label = "Enable" if is_disabled else "Disable"
        status = "Disabled" if is_disabled else "Enabled"
        status_class = (
            "bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300"
            if is_disabled
            else "bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-300"
        )
        return el(
            "div",
            el(
                "div",
                el(
                    "h3",
                    descriptor.display_name,
                    class_="text-base font-semibold text-foreground",
                ),
                el(
                    "p",
                    descriptor.description,
                    class_="text-sm text-muted-foreground mt-1",
                ),
                el(
                    "span",
                    f"v{descriptor.version}",
                    class_="text-xs text-muted-foreground",
                ),
                class_="flex-1",
            ),
            el(
                "span",
                status,
                class_=f"px-2 py-1 rounded text-xs font-medium {status_class}",
            ),
            el(
                "form",
                el("input", type_="hidden", name="plugin", value=descriptor.name),
                el(
                    "input",
                    type_="hidden",
                    name="csrf_token",
                    value=self._get_csrf_token(request),
                ),
                el(
                    "button",
                    label,
                    type_="submit",
                    class_="px-3 py-1.5 rounded text-sm bg-primary-600 text-white hover:bg-primary-700",
                ),
                method="post",
                action="/admin/plugins/toggle",
                class_="ml-4",
            ),
            class_="flex items-center gap-4 p-4",
        )

    def _is_known(self, descriptor: PluginDescriptor, name: str) -> bool:
        """Return True when *name* matches this descriptor's plugin name."""
        return descriptor.name == name

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _user_permissions(request: Request) -> frozenset[str]:
        """Return the requesting user's permission set (empty when unknown)."""
        user = getattr(getattr(request, "state", None), "user", None)
        return frozenset(getattr(user, "permissions", None) or ())

    def _user_is_superadmin(self, request: Request) -> bool:
        """Return True when the requesting user holds the superadmin role."""
        role = (self._rbac_config or AdminRbacConfig()).super_admin_role
        user = getattr(getattr(request, "state", None), "user", None)
        return is_super_admin(user, role)

    def _user_can_manage(self, request: Request) -> bool:
        """Return True when the user may toggle plugins."""
        return self._user_is_superadmin(request) or self._user_permissions(
            request
        ).issuperset(_REQUIRED_PERMISSIONS)

    def _get_csrf_token(self, request: Request) -> str:
        """Return a CSRF token, creating and persisting the session id."""
        if self._csrf_service is None:
            return ""
        csrf_session_id = str(request.session.get("csrf_session_id", ""))
        if not csrf_session_id:
            csrf_session_id = secrets.token_hex(16)
            request.session["csrf_session_id"] = csrf_session_id
        return self._csrf_service.generate_token(csrf_session_id)

    def _csrf_ok(self, request: Request, csrf_token: str) -> bool:
        """Validate the submitted CSRF token against the session id."""
        csrf_session_id = str(request.session.get("csrf_session_id", ""))
        return bool(
            csrf_session_id
            and self._csrf_service
            and self._csrf_service.validate_token(csrf_session_id, csrf_token)
        )

    async def _audit(
        self,
        request: Request,
        success: bool,
        **metadata: Any,
    ) -> None:
        """Log a plugin toggle to the security audit log, best-effort."""
        if not self._audit_service:
            return
        try:
            from lexigram.admin.auth.types import AdminSecurityEventType

            client = getattr(request, "client", None)
            await self._audit_service.log_event(
                event_type=AdminSecurityEventType.SETTINGS_UPDATED,
                ip_address=getattr(client, "host", "unknown"),
                user_agent=request.headers.get("user-agent", "") or "",
                success=success,
                metadata=metadata,
            )
        except Exception:  # noqa: BLE001 — audit failures must not break toggles
            logger.warning("plugins.audit_failed", **metadata)

    @staticmethod
    def _error_redirect(url: str, message: str) -> RedirectResponse:
        """Return a 302 redirect carrying an error flash message."""
        return RedirectResponse(
            url=f"{url}?error={quote_plus(message)}",
            status_code=302,
        )
