"""First-run setup controller for Lexigram Admin.

Provides the initial account creation wizard shown when no admin users exist.
The SetupMiddleware redirects all admin requests here until at least one
admin account has been created.
"""

from __future__ import annotations

import hmac
import secrets
from typing import Any
from urllib.parse import quote_plus

from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse

from lexigram.admin.auth.protocols import (
    AdminAuditLogServiceProtocol,
    AdminCsrfServiceProtocol,
    AdminEmailVerificationServiceProtocol,
    AdminPasswordPolicyServiceProtocol,
)
from lexigram.admin.auth.store import AdminUserStoreProtocol
from lexigram.admin.auth.types import AdminSecurityEventType
from lexigram.admin.config import AdminConfig, AdminRbacConfig
from lexigram.admin.controllers.base import AdminController
from lexigram.admin.engine.renderer import AdminRenderer
from lexigram.admin.lib.template import render_setup_page
from lexigram.admin.resources.urls import admin_prefix_from_request
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
        config: AdminConfig,
        user_store: AdminUserStoreProtocol,
        password_policy_service: AdminPasswordPolicyServiceProtocol,
        audit_service: AdminAuditLogServiceProtocol,
        csrf_service: AdminCsrfServiceProtocol,
        renderer: AdminRenderer,
        task_manager: TaskManagerProtocol | None = None,
        email_verification_service: AdminEmailVerificationServiceProtocol | None = None,
        rbac_config: AdminRbacConfig | None = None,
    ) -> None:
        """Initialise setup controller.

        Args:
            config: Admin configuration; the optional setup token is read
                from ``config.auth.security.setup_token`` (single enforcement
                source, env var ``ADMIN_SETUP_TOKEN`` honored via alias).
            user_store: Store used to check and create admin accounts.
            password_policy_service: Validates passwords against all configured
                policy rules; returns every violation, not just the first.
            audit_service: Records security events; guaranteed never to raise.
            csrf_service: Generates and validates CSRF tokens for the
                pre-session setup form (bypassed by the CSRF middleware).
            renderer: AdminRenderer required by AdminController base.
            task_manager: Optional; injected by container in production.
            email_verification_service: Optional email verification
                orchestrator; when present and the gate applies to the new
                account, a verification email is sent and the user is
                informed after creation.
            rbac_config: Optional; the resolved RBAC config whose
                ``super_admin_role`` names the role granted to the first
                admin account.
        """
        super().__init__(renderer, task_manager)
        self._config = config
        self._user_store = user_store
        self._password_policy_service = password_policy_service
        self._audit_service = audit_service
        self._csrf_service = csrf_service
        self._email_verification_service = email_verification_service
        self._rbac_config = rbac_config

    def _render_setup_page(self, request: Request, **kwargs: Any) -> str:
        """Render setup with every action and asset URL under this mount."""
        return render_setup_page(
            login_url=self._admin_path(request, "/admin/login"),
            setup_url=self._admin_path(request, "/admin/setup"),
            base_url=self._admin_path(request).rstrip("/"),
            **kwargs,
        )

    def _fresh_csrf(self, request: Request) -> str:
        """Generate a fresh session-scoped CSRF token for the setup form."""
        csrf_session_id = secrets.token_urlsafe(16)
        request.session["csrf_session_id"] = csrf_session_id
        return self._csrf_service.generate_token(csrf_session_id)

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
        required_token = self._config.auth.security.setup_token
        try:
            count = await self._user_store.get_admin_count()
        except (RuntimeError, ValueError, OSError) as e:
            logger.warning("setup.count_failed error=%s", e)
            html = self._render_setup_page(
                request,
                error="Unable to verify setup status. Database may be unavailable.",
                csrf_token=self._fresh_csrf(request),
                setup_token_required=bool(required_token),
            )
            return HTMLResponse(content=html, status_code=503)
        if count > 0:
            html = self._render_setup_page(
                request,
                locked=True,
                error="Setup is already complete. Please log in with your existing account.",
            )
            return HTMLResponse(content=html, status_code=200)

        error = request.query_params.get("error", "")
        html = self._render_setup_page(
            request,
            error=error,
            csrf_token=self._fresh_csrf(request),
            setup_token_required=bool(required_token),
        )
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
        required_token = self._config.auth.security.setup_token
        try:
            count = await self._user_store.get_admin_count()
        except (RuntimeError, ValueError, OSError) as e:
            logger.warning("setup.count_failed error=%s", e)
            html = self._render_setup_page(
                request,
                error="Unable to verify setup status. Database may be unavailable.",
                csrf_token=self._fresh_csrf(request),
                setup_token_required=bool(required_token),
            )
            return HTMLResponse(content=html, status_code=503)
        if count > 0:
            html = self._render_setup_page(
                request,
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
        csrf_token = str(form_data.get("csrf_token", ""))

        ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")

        # ── CSRF validation ────────────────────────────────────────────
        csrf_session_id = request.session.get("csrf_session_id", "")
        if not csrf_session_id or not self._csrf_service.validate_token(
            csrf_session_id, csrf_token
        ):
            logger.warning("setup.csrf_validation_failed", ip=ip)
            html = self._render_setup_page(
                request,
                error="Invalid or expired security token. Please reload the page and try again.",
                csrf_token=self._fresh_csrf(request),
                setup_token_required=bool(required_token),
            )
            return HTMLResponse(content=html, status_code=422)

        # ── Optional setup-token guard ─────────────────────────────────
        required_token_str = (
            required_token.get_secret_value() if required_token is not None else None
        )
        if required_token_str and not hmac.compare_digest(
            setup_token_input, required_token_str
        ):
            logger.warning("setup.token_mismatch", ip=ip)
            await self._audit_service.log_event(
                event_type=AdminSecurityEventType.SETUP_BLOCKED,
                ip_address=ip,
                user_agent=user_agent,
                success=False,
                metadata={"reason": "invalid_setup_token"},
            )
            html = self._render_setup_page(
                request,
                error="Invalid setup token.",
                csrf_token=self._fresh_csrf(request),
                setup_token_required=bool(required_token),
            )
            return HTMLResponse(content=html, status_code=403)

        # ── Basic field presence ───────────────────────────────────────
        if not name or not email or not password:
            html = self._render_setup_page(
                request,
                error="All fields are required.",
                csrf_token=self._fresh_csrf(request),
                setup_token_required=bool(required_token),
            )
            return HTMLResponse(content=html, status_code=422)

        if password != confirm:
            html = self._render_setup_page(
                request,
                error="Passwords do not match.",
                csrf_token=self._fresh_csrf(request),
                setup_token_required=bool(required_token),
            )
            return HTMLResponse(content=html, status_code=422)

        # ── Full password policy validation (all violations) ───────────
        policy_result = self._password_policy_service.validate(password, email=email)
        if not policy_result.is_valid:
            violation_lines = "\n".join(
                f"• {v.message}" for v in policy_result.violations
            )
            html = self._render_setup_page(
                request,
                error=violation_lines,
                csrf_token=self._fresh_csrf(request),
                setup_token_required=bool(required_token),
            )
            return HTMLResponse(content=html, status_code=422)

        # ── Hash and persist ───────────────────────────────────────────
        hashed_password = _hash_password(password)

        try:
            created_result = await self._user_store.claim_first_admin(
                name=name,
                email=email,
                hashed_password=hashed_password,
                roles=[(self._rbac_config or AdminRbacConfig()).super_admin_role],
            )
        except Exception as exc:
            # Treat any persistence failure (duplicate email, DB error, etc.)
            # as a non-fatal setup error that is shown back to the user.
            # Full detail goes to the log; the page gets a humanized message
            # (no [LEX_ERR_*] codes or docs links).
            from lexigram.admin.controllers._errors import humanize_error

            logger.error("setup.create_user_failed", email=email, error=str(exc))
            html = self._render_setup_page(
                request,
                error=(
                    "Failed to create account: "
                    + humanize_error(str(exc), fallback="an internal error occurred.")
                ),
                csrf_token=self._fresh_csrf(request),
                setup_token_required=bool(required_token),
            )
            return HTMLResponse(content=html, status_code=422)

        if created_result.is_err():
            # Another submission created the first admin between the
            # pre-flight count check and this insert — lock the wizard.
            html = self._render_setup_page(
                request,
                locked=True,
                error="Setup is already complete. Please log in with your existing account.",
            )
            return HTMLResponse(content=html, status_code=200)
        created = created_result.unwrap()

        logger.info("setup.first_admin_created", email=email)

        await self._audit_service.log_event(
            event_type=AdminSecurityEventType.SETUP_COMPLETED,
            ip_address=ip,
            user_agent=user_agent,
            success=True,
            metadata={"email": email},
        )

        notice = ""
        user_id = str(getattr(created, "user_id", "") or getattr(created, "id", ""))
        if (
            self._email_verification_service is not None
            and user_id
            and await self._email_verification_service.is_required(user_id)
        ):
            # The operator just proved control of this deployment with the
            # setup token — that is a stronger ownership proof than an
            # emailed link. Mark the first admin verified directly instead
            # of gating the only account on email delivery (a fresh install
            # frequently has no mailer configured yet, which would lock the
            # operator out entirely).
            mark_verified = getattr(
                self._email_verification_service, "mark_verified", None
            )
            if callable(mark_verified):
                try:
                    await mark_verified(user_id)
                    logger.info("setup.first_admin_email_auto_verified", email=email)
                except Exception as exc:  # noqa: BLE001 — never fail setup on this
                    logger.error(
                        "setup.first_admin_auto_verify_failed",
                        email=email,
                        error=str(exc),
                    )
            else:
                # Custom verification service without mark_verified — fall
                # back to the legacy email flow.
                send_result = await self._email_verification_service.send_verification(
                    user_id=user_id,
                    email=email,
                    user_name=name,
                    base_url=str(request.base_url),
                    ip_address=ip,
                    admin_prefix=admin_prefix_from_request(request),
                )
                if send_result.is_ok():
                    notice = (
                        f"Account created successfully — a verification email was "
                        f"sent to {email}. Please verify your email before signing in."
                    )
                else:
                    logger.error(
                        "setup.verification_send_failed",
                        email=email,
                        error=str(send_result.unwrap_err()),
                    )
                    notice = (
                        "Account created successfully — email verification is "
                        "enabled, and you will be asked to verify your email "
                        "before signing in."
                    )

        admin_home = self._admin_path(request)
        url = f"{self._admin_path(request, '/admin/login')}?next={admin_home}"
        if notice:
            url += "&notice=" + quote_plus(notice)
        return RedirectResponse(url=url, status_code=302)

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
    """Hash a plain-text password using bcrypt.

    Bcrypt with 12 rounds is used.  A missing ``bcrypt`` package raises
    ``RuntimeError`` (fail-closed) instead of degrading to SHA-256.

    Args:
        plain: Plain-text password string.

    Returns:
        Hashed password string suitable for storage.

    Raises:
        RuntimeError: When the ``bcrypt`` package is not installed.
    """
    from lexigram.admin.lib.password import hash_password

    return hash_password(plain)


__all__ = ["SetupController"]
