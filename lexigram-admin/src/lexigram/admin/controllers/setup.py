"""First-run setup controller for Lexigram Admin.

Provides the initial account creation wizard shown when no admin users exist.
The SetupMiddleware redirects all admin requests here until at least one
admin account has been created.
"""

from __future__ import annotations

import hashlib
import os

from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse

from lexigram.admin.auth.protocols import (
    AdminAuditLogServiceProtocol,
    AdminPasswordPolicyServiceProtocol,
)
from lexigram.admin.auth.store import AdminUserStoreProtocol
from lexigram.admin.auth.types import AdminSecurityEventType
from lexigram.admin.controllers.base import AdminController
from lexigram.admin.engine.renderer import AdminRenderer
from lexigram.admin.lib.template import render_setup_page
from lexigram.contracts.core import TaskManagerProtocol
from lexigram.contracts.web import get, post
from lexigram.di.decorators import inject
from lexigram.logging import get_logger

logger = get_logger(__name__)


@inject
class SetupController(AdminController):
    """First-run setup wizard controller.

    Provides:
    - GET  /setup — Display account creation form
    - POST /setup — Create the first admin account
    """

    prefix = ""

    def __init__(
        self,
        user_store: AdminUserStoreProtocol,
        password_policy_service: AdminPasswordPolicyServiceProtocol,
        audit_service: AdminAuditLogServiceProtocol,
        renderer: AdminRenderer,
        task_manager: TaskManagerProtocol | None = None,
    ) -> None:
        """Initialise setup controller.

        Args:
            user_store: Store used to check and create admin accounts.
            password_policy_service: Validates passwords against all configured
                policy rules; returns every violation, not just the first.
            audit_service: Records security events; guaranteed never to raise.
            renderer: AdminRenderer required by AdminController base.
            task_manager: Optional; injected by container in production.
        """
        super().__init__(renderer, task_manager)
        self._user_store = user_store
        self._password_policy_service = password_policy_service
        self._audit_service = audit_service

    # ------------------------------------------------------------------
    # GET /setup
    # ------------------------------------------------------------------

    @get("/setup")
    async def setup_form(self, request: Request) -> HTMLResponse | RedirectResponse:
        """Display the first-run setup form.

        If at least one admin account already exists, a locked message is shown
        so the user knows to log in with their existing credentials.

        Args:
            request: Incoming HTTP request.

        Returns:
            HTMLResponse with the rendered setup page.
        """
        try:
            count = await self._user_store.get_admin_count()
        except (RuntimeError, ValueError, OSError) as e:
            logger.warning("setup.count_failed error=%s", e)
            html = render_setup_page(
                error="Unable to verify setup status. Database may be unavailable."
            )
            return HTMLResponse(content=html, status_code=503)
        if count > 0:
            html = render_setup_page(
                locked=True,
                error="Setup is already complete. Please log in with your existing account.",
            )
            return HTMLResponse(content=html, status_code=200)

        error = request.query_params.get("error", "")
        html = render_setup_page(error=error)
        return HTMLResponse(content=html)

    # ------------------------------------------------------------------
    # POST /setup
    # ------------------------------------------------------------------

    @post("/setup")
    async def setup_submit(self, request: Request) -> HTMLResponse | RedirectResponse:
        """Process the first-run setup form and create the initial admin account.

        Validates the optional setup token, enforces the full password policy
        (all violations reported simultaneously), hashes the password with
        bcrypt, persists the user, audits the outcome, then redirects to the
        login page.

        Args:
            request: Incoming HTTP request carrying form data.

        Returns:
            RedirectResponse to ``/admin/login?next=/admin/`` on success, or
            an HTMLResponse re-rendering the setup form with error details on
            any validation or persistence failure.
        """
        try:
            count = await self._user_store.get_admin_count()
        except (RuntimeError, ValueError, OSError) as e:
            logger.warning("setup.count_failed error=%s", e)
            html = render_setup_page(
                error="Unable to verify setup status. Database may be unavailable."
            )
            return HTMLResponse(content=html, status_code=503)
        if count > 0:
            html = render_setup_page(
                locked=True,
                error="Setup is already complete. Please log in with your existing account.",
            )
            return HTMLResponse(content=html, status_code=200)

        form_data = await request.form()
        name = str(form_data.get("name", "")).strip()
        email = str(form_data.get("email", "")).strip()
        password = str(form_data.get("password", "")).strip()
        confirm = str(form_data.get("confirm_password", "")).strip()
        setup_token_input = str(form_data.get("setup_token", "")).strip()

        ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")

        # ── Optional setup-token guard ─────────────────────────────────
        required_token = os.environ.get("ADMIN_SETUP_TOKEN", "")
        if required_token and setup_token_input != required_token:
            logger.warning("setup.token_mismatch", ip=ip)
            await self._audit_service.log_event(
                event_type=AdminSecurityEventType.SETUP_BLOCKED,
                ip_address=ip,
                user_agent=user_agent,
                success=False,
                metadata={"reason": "invalid_setup_token"},
            )
            html = render_setup_page(error="Invalid setup token.")
            return HTMLResponse(content=html, status_code=403)

        # ── Basic field presence ───────────────────────────────────────
        if not name or not email or not password:
            html = render_setup_page(error="All fields are required.")
            return HTMLResponse(content=html, status_code=422)

        if password != confirm:
            html = render_setup_page(error="Passwords do not match.")
            return HTMLResponse(content=html, status_code=422)

        # ── Full password policy validation (all violations) ───────────
        policy_result = self._password_policy_service.validate(password, email=email)
        if not policy_result.is_valid:
            violation_lines = "\n".join(
                f"• {v.message}" for v in policy_result.violations
            )
            html = render_setup_page(error=violation_lines)
            return HTMLResponse(content=html, status_code=422)

        # ── Hash and persist ───────────────────────────────────────────
        hashed_password = _hash_password(password)

        try:
            await self._user_store.create_user(
                name=name,
                email=email,
                hashed_password=hashed_password,
                roles=["superadmin"],
            )
        except Exception as exc:
            # Treat any persistence failure (duplicate email, DB error, etc.)
            # as a non-fatal setup error that is shown back to the user.
            logger.error("setup.create_user_failed", email=email, error=str(exc))
            html = render_setup_page(error=f"Failed to create account: {exc}")
            return HTMLResponse(content=html, status_code=422)

        logger.info("setup.first_admin_created", email=email)

        await self._audit_service.log_event(
            event_type=AdminSecurityEventType.SETUP_COMPLETED,
            ip_address=ip,
            user_agent=user_agent,
            success=True,
            metadata={"email": email},
        )

        return RedirectResponse(url="/admin/login?next=/admin/", status_code=302)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_client_ip(self, request: Request) -> str:
        """Extract the real client IP from the request.

        Prefers the first value of the ``X-Forwarded-For`` header when present
        (set by reverse proxies), falling back to the direct TCP peer address.

        Args:
            request: Incoming HTTP request.

        Returns:
            IP address string, or ``"unknown"`` when unavailable.
        """
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"


def _hash_password(plain: str) -> str:
    """Hash a plain-text password using bcrypt, falling back to SHA-256.

    Bcrypt with 12 rounds is the default.  SHA-256 is used only when the
    ``bcrypt`` package is not installed (e.g. lightweight test environments).

    Args:
        plain: Plain-text password string.

    Returns:
        Hashed password string suitable for storage.
    """
    try:
        import bcrypt

        hashed = bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=12))
        return hashed.decode("utf-8")
    except ImportError:
        return hashlib.sha256(plain.encode()).hexdigest()


__all__ = ["SetupController"]
