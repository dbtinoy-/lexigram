"""Built-in authentication controller for Lexigram Admin.

Provides login/logout endpoints with standalone UI (no admin shell).
"""

from __future__ import annotations

import secrets
from urllib.parse import quote_plus

from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse

from lexigram.admin.auth.protocols import (
    AdminAuthServiceProtocol,
    AdminCsrfServiceProtocol,
)
from lexigram.admin.controllers.base import AdminController
from lexigram.admin.engine.renderer import AdminRenderer
from lexigram.admin.lib.template import render_login_page
from lexigram.admin.observability.admin_metrics import AdminMetrics
from lexigram.contracts.core import TaskManagerProtocol
from lexigram.contracts.web import get, post
from lexigram.di.decorators import inject
from lexigram.logging import get_logger

logger = get_logger(__name__)


@inject
class AuthController(AdminController):
    """Built-in authentication controller.

    Provides:
    - GET /admin/login  — Standalone login page with CSRF token
    - POST /admin/login — Process login credentials through the full auth pipeline
    - GET /admin/logout — Invalidate session and redirect to login
    """

    prefix = ""

    def __init__(
        self,
        auth_service: AdminAuthServiceProtocol,
        csrf_service: AdminCsrfServiceProtocol,
        renderer: AdminRenderer,
        task_manager: TaskManagerProtocol | None = None,
        metrics: AdminMetrics | None = None,
    ) -> None:
        """Initialise auth controller.

        Args:
            auth_service: Orchestrates credential verification, rate limiting,
                lockout checks, session issuance, and audit logging.
            csrf_service: Generates and validates CSRF tokens.
            renderer: AdminRenderer for page rendering.
            task_manager: Optional task manager; injected by the container in
                production, omitted in tests.
            metrics: Optional admin metrics collector.
        """
        super().__init__(renderer, task_manager)
        self._auth_service = auth_service
        self._csrf_service = csrf_service
        self._metrics = metrics or AdminMetrics(None)

    # ------------------------------------------------------------------
    # GET /login
    # ------------------------------------------------------------------

    @get("/login")
    async def login_form(self, request: Request) -> HTMLResponse | RedirectResponse:
        """Display the standalone login form.

        Redirects authenticated users to *next_url*.  For unauthenticated
        visitors a fresh CSRF token is embedded in the rendered form.

        Args:
            request: Incoming HTTP request.

        Returns:
            HTMLResponse with the rendered login page, or a RedirectResponse
            when the user is already authenticated.
        """
        next_url = request.query_params.get("next", "/admin/")

        user = getattr(request.state, "user", None)
        if user and user.user_id != "guest":
            return RedirectResponse(url=next_url, status_code=302)

        error = request.query_params.get("error", "")

        csrf_session_id = secrets.token_urlsafe(16)
        request.session["csrf_session_id"] = csrf_session_id
        csrf_token = self._csrf_service.generate_token(csrf_session_id)

        html = render_login_page(next_url=next_url, error=error, csrf_token=csrf_token)
        return HTMLResponse(content=html)

    # ------------------------------------------------------------------
    # POST /login
    # ------------------------------------------------------------------

    @post("/login")
    async def login_submit(self, request: Request) -> RedirectResponse:
        """Process login form submission through the full security pipeline.

        Validates the CSRF token, resolves the client IP, and delegates
        credential verification to ``AdminAuthServiceProtocol.authenticate``.
        On success the session is populated and the user is redirected to
        *next_url*.  On failure the login page is re-shown with a descriptive
        error message.

        Args:
            request: Incoming HTTP request carrying form data.

        Returns:
            RedirectResponse to *next_url* on success, or back to the login
            page with an error query parameter on failure.
        """
        form_data = await request.form()
        email = str(form_data.get("email", ""))
        password = str(form_data.get("password", ""))
        next_url = str(form_data.get("next", "/admin/"))
        csrf_token = str(form_data.get("csrf_token", ""))

        # ── CSRF validation ────────────────────────────────────────────
        csrf_session_id = request.session.get("csrf_session_id", "")
        if not csrf_session_id or not self._csrf_service.validate_token(
            csrf_session_id, csrf_token
        ):
            logger.warning(
                "auth.csrf_validation_failed", ip=self._get_client_ip(request)
            )
            return RedirectResponse(
                url=f"/admin/login?error={quote_plus('Invalid or expired security token. Please try again.')}&next={quote_plus(next_url)}",
                status_code=302,
            )

        # ── Basic input guard ──────────────────────────────────────────
        if not email or not password:
            return RedirectResponse(
                url=f"/admin/login?error={quote_plus('Email and password are required.')}&next={quote_plus(next_url)}",
                status_code=302,
            )

        # ── Resolve client context ─────────────────────────────────────
        ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")

        logger.info("auth.login_attempt", email=email, ip=ip)

        result = await self._auth_service.authenticate(email, password, ip, user_agent)

        if result.is_ok():
            auth_result = result.unwrap()
            request.session["admin_user_id"] = auth_result.user_id
            request.session["admin_user_email"] = auth_result.email
            if hasattr(auth_result, "session_id"):
                request.session["session_id"] = auth_result.session_id
            self._metrics.record_login(status="success")
            logger.info(
                "auth.login_success",
                user_id=auth_result.user_id,
                email=auth_result.email,
                redirect=next_url,
            )
            return RedirectResponse(url=next_url, status_code=302)

        error_msg = str(result.unwrap_err())
        self._metrics.record_login(status="failure")
        logger.warning("auth.login_failed", email=email, ip=ip, reason=error_msg)
        return RedirectResponse(
            url=f"/admin/login?error={quote_plus(error_msg)}&next={quote_plus(next_url)}",
            status_code=302,
        )

    # ------------------------------------------------------------------
    # GET /logout
    # ------------------------------------------------------------------

    @get("/logout")
    async def logout(self, request: Request) -> RedirectResponse:
        """Invalidate the current session and redirect to the login page.

        Calls ``AdminAuthServiceProtocol.invalidate_session`` before clearing
        the Starlette session cookie so that any server-side session record is
        also revoked.

        Args:
            request: Incoming HTTP request.

        Returns:
            RedirectResponse to /admin/login.
        """
        session_id = request.session.get("session_id")
        if session_id:
            await self._auth_service.invalidate_session(session_id)
            logger.info("auth.logout", session_id=session_id)

        request.session.clear()
        return RedirectResponse(url="/admin/login", status_code=302)

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


__all__ = ["AuthController"]
