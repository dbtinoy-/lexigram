"""User profile controller for the admin interface.

Renders the authenticated user's profile page inside the admin shell and
handles password changes.  Two-factor authentication management lives on
the dedicated ``/admin/profile/mfa`` screen (AuthController); this page
surfaces its status and links to it.
"""

from __future__ import annotations

from secrets import token_hex
from typing import Any
from urllib.parse import quote_plus

from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

from lexigram.admin.auth.models import AdminUser
from lexigram.admin.auth.protocols import (
    AdminAuditLogServiceProtocol,
    AdminCsrfServiceProtocol,
    AdminMfaServiceProtocol,
)
from lexigram.admin.auth.store.protocols import AdminUserStoreProtocol
from lexigram.admin.auth.types import AdminSecurityEventType
from lexigram.admin.controllers.base import AdminController
from lexigram.admin.engine.renderer import AdminRenderer
from lexigram.admin.lib.template import render_profile_page
from lexigram.contracts.web import get, post
from lexigram.logging import get_logger

logger = get_logger(__name__)

__all__ = ["ProfileController"]


class ProfileController(AdminController):
    """Profile management controller.

    Routes:
        GET  /admin/profile            - Profile page (admin shell)
        POST /admin/profile/password   - Change the current user's password
    """

    prefix = "/profile"

    def __init__(
        self,
        renderer: AdminRenderer,
        csrf_service: AdminCsrfServiceProtocol | None = None,
        mfa_service: AdminMfaServiceProtocol | None = None,
    ) -> None:
        """Initialise the profile controller.

        Args:
            renderer: AdminRenderer for shell page rendering.
            csrf_service: Optional CSRF token service.
            mfa_service: Optional 2FA service; ``None`` hides MFA state.
        """
        super().__init__(renderer=renderer)
        self._csrf_service = csrf_service
        self._mfa_service = mfa_service
        self._user_store: AdminUserStoreProtocol | None = None

    # -- helpers --

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
        """Validate the submitted CSRF token against the session id.

        Args:
            request: Incoming HTTP request (session already loaded).
            csrf_token: Token submitted with the form.

        Returns:
            ``True`` when the token matches the session.
        """
        if self._csrf_service is None:
            return True
        csrf_session_id = str(request.session.get("csrf_session_id", ""))
        return bool(
            csrf_session_id
            and self._csrf_service.validate_token(csrf_session_id, csrf_token)
        )

    @staticmethod
    def _redirect(url: str, message: str, is_error: bool = False) -> Response:
        """Return a 302 redirect carrying an error or notice flash message."""
        key = "error" if is_error else "notice"
        return RedirectResponse(
            url=f"{url}?{key}={quote_plus(message)}",
            status_code=302,
        )

    async def _audit(
        self,
        request: Request,
        event_type: AdminSecurityEventType,
        success: bool,
        **metadata: Any,
    ) -> None:
        """Append a security audit event, best-effort."""
        try:
            container = getattr(request.state, "container", None)
            if container is None:
                return
            audit_service = await container.resolve(
                AdminAuditLogServiceProtocol,
            )
            client = getattr(request, "client", None)
            await audit_service.log_event(
                event_type=event_type,
                ip_address=getattr(client, "host", "unknown"),
                user_agent=request.headers.get("user-agent", "") or "",
                success=success,
                metadata=metadata,
            )
        except Exception:  # noqa: BLE001 — audit failures must not break requests
            logger.warning("profile.audit_failed", event_type=event_type.value)

    # -- routes --

    @get("/")
    async def profile_page(self, request: Request) -> Response:
        """Render the current user's profile page inside the admin shell.

        Args:
            request: Incoming HTTP request (authenticated).

        Returns:
            HTMLResponse with the profile page, or a redirect to login
            when unauthenticated.
        """
        user: AdminUser = self.current_user(request)
        if not user or user.user_id == "guest":
            return RedirectResponse(
                url=f"{self._admin_path(request, '/admin/login')}?next={quote_plus(self._admin_path(request, '/admin/profile'))}",
                status_code=302,
            )

        mfa_enabled = False
        if self._mfa_service is not None:
            try:
                mfa_enabled = await self._mfa_service.is_enabled(str(user.user_id))
            except Exception:  # noqa: BLE001 — non-fatal for page rendering
                logger.warning("profile.mfa_status_failed")

        html = render_profile_page(
            name=user.name or user.email,
            email=user.email,
            roles=list(getattr(user, "roles", None) or ()),
            user_id=str(user.user_id),
            mfa_enabled=mfa_enabled,
            csrf_token=self._csrf_token(request),
            current_password_err=str(
                request.query_params.get("current_password_err", "")
            ),
            new_password_err=str(request.query_params.get("new_password_err", "")),
            confirmation_err=str(request.query_params.get("confirmation_err", "")),
            mfa_url=self._admin_path(request, "/admin/profile/mfa"),
            password_url=self._admin_path(request, "/admin/profile/password"),
        )
        from lexigram.admin.state.context import AdminContextManager

        async with AdminContextManager(request) as ctx:
            error = request.query_params.get("error", "")
            notice = request.query_params.get("notice", "")
            if error:
                ctx.add_flash(error, "error")
            if notice:
                ctx.add_flash(notice, "success")
            return await self.render_admin(
                request,
                html,
                title="Profile",
                breadcrumbs=self.generate_breadcrumbs(
                    ("Home", self._admin_path(request)),
                    current="Profile",
                ),
            )

    @post("/password")
    async def password_submit(self, request: Request) -> Response:
        """Change the current user's password.

        Validates CSRF, verifies the current password, and persists the new
        hash through the admin user store.  The session is left intact.

        Args:
            request: Incoming HTTP request carrying form data.

        Returns:
            RedirectResponse back to the profile page with a notice or
            error flash message.
        """
        user: AdminUser = self.current_user(request)
        if not user or user.user_id == "guest":
            return RedirectResponse(
                url=f"{self._admin_path(request, '/admin/login')}?next={quote_plus(self._admin_path(request, '/admin/profile'))}",
                status_code=302,
            )
        if self._user_store is None:
            return self._redirect(
                self._admin_path(request, "/admin/profile"),
                "Password change is unavailable.",
                True,
            )

        form = request.scope.get("admin_form_data") or await request.form()
        csrf_token = str(form.get("csrf_token", ""))
        current = str(form.get("current_password", ""))
        new_password = str(form.get("new_password", ""))
        confirmation = str(form.get("new_password_confirmation", ""))

        if not self._csrf_ok(request, csrf_token):
            return self._redirect(
                self._admin_path(request, "/admin/profile"),
                "Invalid or expired security token. Please try again.",
                True,
            )
        if not current or not new_password or not confirmation:
            params = [
                p
                for p in (
                    "current_password_err=Current%20password%20is%20required."
                    if not current
                    else "",
                    "new_password_err=New%20password%20is%20required."
                    if not new_password
                    else "",
                    "confirmation_err=Please%20confirm%20the%20new%20password."
                    if not confirmation
                    else "",
                )
                if p
            ]
            return RedirectResponse(
                url=f"{self._admin_path(request, '/admin/profile')}?{'&'.join(params)}",
                status_code=302,
            )
        if len(new_password) < 8:
            return RedirectResponse(
                url=f"{self._admin_path(request, '/admin/profile')}?new_password_err="
                + quote_plus("New password must be at least 8 characters."),
                status_code=302,
            )
        if new_password != confirmation:
            return RedirectResponse(
                url=f"{self._admin_path(request, '/admin/profile')}?confirmation_err="
                + quote_plus("New passwords do not match."),
                status_code=302,
            )

        authenticated = await self._user_store.authenticate(user.email, current)
        if authenticated is None:
            logger.warning("profile.password_verify_failed", email=user.email)
            return self._redirect(
                self._admin_path(request, "/admin/profile"),
                "Current password is incorrect.",
                True,
            )

        from lexigram.admin.lib.password import hash_password

        record = await self._user_store.get_user_by_email(user.email)
        if record is None:
            return self._redirect(
                self._admin_path(request, "/admin/profile"),
                "Account not found. Please sign in again.",
                True,
            )
        record.hashed_password = hash_password(new_password)
        await self._user_store.update_user(record)

        await self._audit(
            request,
            AdminSecurityEventType.PASSWORD_CHANGED,
            success=True,
            email=user.email,
        )
        logger.info("profile.password_changed", email=user.email)
        return self._redirect(
            self._admin_path(request, "/admin/profile"),
            "Password updated successfully.",
        )
