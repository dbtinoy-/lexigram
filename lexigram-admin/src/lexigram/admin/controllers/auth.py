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
    AdminEmailOtpServiceProtocol,
    AdminEmailVerificationServiceProtocol,
    AdminMfaServiceProtocol,
    AdminPasswordResetServiceProtocol,
)
from lexigram.admin.controllers.base import AdminController
from lexigram.admin.engine.renderer import AdminRenderer
from lexigram.admin.lib.template import (
    render_email_verified_page,
    render_login_page,
    render_mfa_challenge_page,
    render_mfa_setup_page,
    render_password_reset_confirm_page,
    render_password_reset_request_page,
    render_verify_email_page,
)
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
        password_reset_service: AdminPasswordResetServiceProtocol | None = None,
        mfa_service: AdminMfaServiceProtocol | None = None,
        email_verification_service: AdminEmailVerificationServiceProtocol
        | None = None,
        email_otp_service: AdminEmailOtpServiceProtocol | None = None,
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
            password_reset_service: Optional password reset orchestrator;
                injected by the container when registered, ``None`` otherwise.
            mfa_service: Optional TOTP 2FA orchestrator; injected by the
                container when registered, ``None`` otherwise.
            email_verification_service: Optional email verification
                orchestrator; ``None`` disables the verification gate.
            email_otp_service: Optional email OTP factor orchestrator;
                ``None`` disables email-code challenges.
        """
        super().__init__(renderer, task_manager)
        self._auth_service = auth_service
        self._csrf_service = csrf_service
        self._metrics = metrics or AdminMetrics(None)
        self._password_reset_service = password_reset_service
        self._mfa_service = mfa_service
        self._email_verification_service = email_verification_service
        self._email_otp_service = email_otp_service

    def _fresh_csrf(self, request: Request) -> str:
        """Generate a fresh CSRF token bound to a new session id."""
        csrf_session_id = secrets.token_urlsafe(16)
        request.session["csrf_session_id"] = csrf_session_id
        return self._csrf_service.generate_token(csrf_session_id)

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
        notice = request.query_params.get("notice", "")

        csrf_session_id = secrets.token_urlsafe(16)
        request.session["csrf_session_id"] = csrf_session_id
        csrf_token = self._csrf_service.generate_token(csrf_session_id)

        html = render_login_page(
            next_url=next_url,
            error=error,
            csrf_token=csrf_token,
            notice=notice,
        )
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
            if auth_result.mfa_required:
                # 2FA challenge — park the identity in the session; the
                # /login/2fa flow completes the login with a code.  For the
                # email factor the code is emailed right away.
                factor = "totp"
                if self._mfa_service is not None:
                    factor = await self._mfa_service.get_factor()
                request.session["mfa_pending_user_id"] = auth_result.user_id
                request.session["mfa_pending_email"] = auth_result.email
                request.session["mfa_pending_roles"] = auth_result.roles
                request.session["mfa_pending_next"] = next_url
                request.session["mfa_pending_factor"] = factor
                if factor == "email" and self._email_otp_service is not None:
                    otp_result = await self._email_otp_service.send_otp(
                        user_id=auth_result.user_id,
                        email=auth_result.email,
                        user_name=auth_result.email,
                    )
                    if otp_result.is_err():
                        logger.warning(
                            "auth.login_email_otp_send_failed",
                            user_id=auth_result.user_id,
                            reason=str(otp_result.unwrap_err()),
                        )
                logger.info(
                    "auth.login_mfa_challenge",
                    user_id=auth_result.user_id,
                    email=auth_result.email,
                    factor=factor,
                )
                return RedirectResponse(url="/admin/login/2fa", status_code=302)

            if auth_result.email_verification_required:
                # Verification gate — park the identity so the /verify-email
                # flow can re-send links, then issue one now.
                request.session["verify_pending_user_id"] = auth_result.user_id
                request.session["verify_pending_email"] = auth_result.email
                request.session["verify_pending_next"] = next_url
                if self._email_verification_service is not None:
                    verify_result = await self._email_verification_service.send_verification(
                        user_id=auth_result.user_id,
                        email=auth_result.email,
                        user_name=auth_result.email,
                        base_url=str(request.base_url),
                        ip_address=ip,
                    )
                    if verify_result.is_err():
                        logger.warning(
                            "auth.login_verification_send_failed",
                            user_id=auth_result.user_id,
                            reason=str(verify_result.unwrap_err()),
                        )
                logger.info(
                    "auth.login_verification_required",
                    user_id=auth_result.user_id,
                    email=auth_result.email,
                )
                return RedirectResponse(url="/admin/verify-email", status_code=302)

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
    # GET /login/2fa — challenge form
    # ------------------------------------------------------------------

    @get("/login/2fa")
    async def mfa_challenge_form(self, request: Request) -> HTMLResponse | RedirectResponse:
        """Display the standalone TOTP challenge form.

        Only reachable when a pending 2FA challenge exists in the session
        (parked by ``login_submit``); otherwise the user is redirected to
        the login page.  A fresh CSRF token is embedded in the form.

        Args:
            request: Incoming HTTP request.

        Returns:
            HTMLResponse with the rendered challenge page, or a
            RedirectResponse to /admin/ or /admin/login.
        """
        user = getattr(request.state, "user", None)
        if user and user.user_id != "guest":
            return RedirectResponse(url="/admin/", status_code=302)

        pending_user_id = request.session.get("mfa_pending_user_id", "")
        if not pending_user_id:
            return RedirectResponse(url="/admin/login", status_code=302)

        email = request.session.get("mfa_pending_email", "")
        next_url = request.session.get("mfa_pending_next", "/admin/")
        factor = request.session.get("mfa_pending_factor", "totp")
        error = request.query_params.get("error", "")
        notice = request.query_params.get("notice", "")
        csrf_token = self._fresh_csrf(request)

        html = render_mfa_challenge_page(
            email=email,
            error=error,
            csrf_token=csrf_token,
            next_url=next_url,
            factor=factor,
            resend_notice=notice,
        )
        return HTMLResponse(content=html)

    # ------------------------------------------------------------------
    # POST /login/2fa — challenge submit
    # ------------------------------------------------------------------

    @post("/login/2fa")
    async def mfa_challenge_submit(self, request: Request) -> RedirectResponse:
        """Complete a 2FA challenge and finish the login.

        Verifies the CSRF token, delegates code verification to
        ``AdminAuthServiceProtocol.complete_mfa_login``, and on success
        populates the session exactly like ``login_submit``.  On failure
        the challenge page is re-shown with an error message.

        Args:
            request: Incoming HTTP request carrying form data.

        Returns:
            RedirectResponse to the pending destination on success, or back
            to the challenge page with an error query parameter.
        """
        form_data = await request.form()
        code = str(form_data.get("code", ""))
        csrf_token = str(form_data.get("csrf_token", ""))

        pending_user_id = request.session.get("mfa_pending_user_id", "")
        if not pending_user_id:
            return RedirectResponse(url="/admin/login", status_code=302)

        csrf_session_id = request.session.get("csrf_session_id", "")
        if not csrf_session_id or not self._csrf_service.validate_token(
            csrf_session_id, csrf_token
        ):
            logger.warning(
                "auth.csrf_validation_failed", ip=self._get_client_ip(request)
            )
            return RedirectResponse(
                url=f"/admin/login/2fa?error={quote_plus('Invalid or expired security token. Please try again.')}",
                status_code=302,
            )

        if not code:
            return RedirectResponse(
                url=f"/admin/login/2fa?error={quote_plus('Verification code is required.')}",
                status_code=302,
            )

        ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")

        result = await self._auth_service.complete_mfa_login(
            user_id=pending_user_id,
            email=request.session.get("mfa_pending_email", ""),
            roles=request.session.get("mfa_pending_roles", []),
            code=code,
            ip_address=ip,
            user_agent=user_agent,
        )

        if result.is_err():
            self._metrics.record_login(status="failure")
            error_msg = str(result.unwrap_err())
            logger.warning(
                "auth.mfa_code_failed", user_id=pending_user_id, reason=error_msg
            )
            return RedirectResponse(
                url=f"/admin/login/2fa?error={quote_plus(error_msg)}",
                status_code=302,
            )

        auth_result = result.unwrap()
        next_url = request.session.get("mfa_pending_next", "/admin/")
        request.session["admin_user_id"] = auth_result.user_id
        request.session["admin_user_email"] = auth_result.email
        request.session["session_id"] = auth_result.session_id
        for key in (
            "mfa_pending_user_id",
            "mfa_pending_email",
            "mfa_pending_roles",
            "mfa_pending_next",
            "mfa_pending_factor",
        ):
            request.session.pop(key, None)
        self._metrics.record_login(status="success")
        logger.info(
            "auth.login_success",
            user_id=auth_result.user_id,
            email=auth_result.email,
            redirect=next_url,
        )
        return RedirectResponse(url=next_url, status_code=302)

    # ------------------------------------------------------------------
    # POST /login/2fa/resend — resend email code
    # ------------------------------------------------------------------

    @post("/login/2fa/resend")
    async def mfa_challenge_resend(self, request: Request) -> RedirectResponse:
        """Resend the email verification code for a pending challenge.

        Only valid for the email factor and while a challenge is parked in
        the session.  Cooldown and delivery errors (e.g. "please wait") are
        surfaced on the challenge page.

        Args:
            request: Incoming HTTP request carrying form data.

        Returns:
            RedirectResponse to /admin/login/2fa with a notice on success or
            an error query parameter on failure.
        """
        pending_user_id = request.session.get("mfa_pending_user_id", "")
        if not pending_user_id:
            return RedirectResponse(url="/admin/login", status_code=302)

        form_data = await request.form()
        csrf_token = str(form_data.get("csrf_token", ""))
        csrf_session_id = request.session.get("csrf_session_id", "")
        if not csrf_session_id or not self._csrf_service.validate_token(
            csrf_session_id, csrf_token
        ):
            logger.warning(
                "auth.csrf_validation_failed", ip=self._get_client_ip(request)
            )
            return RedirectResponse(
                url=f"/admin/login/2fa?error={quote_plus('Invalid or expired security token. Please try again.')}",
                status_code=302,
            )

        factor = request.session.get("mfa_pending_factor", "totp")
        if factor != "email" or self._email_otp_service is None:
            return RedirectResponse(
                url=f"/admin/login/2fa?error={quote_plus('Resending codes is not available for this factor.')}",
                status_code=302,
            )

        email = str(form_data.get("email", "")) or request.session.get(
            "mfa_pending_email", ""
        )
        result = await self._email_otp_service.send_otp(
            user_id=pending_user_id,
            email=email,
            user_name=email,
        )
        if result.is_err():
            logger.warning(
                "auth.email_otp_resend_failed",
                user_id=pending_user_id,
                reason=str(result.unwrap_err()),
            )
            return RedirectResponse(
                url=f"/admin/login/2fa?error={quote_plus(str(result.unwrap_err()))}",
                status_code=302,
            )
        return RedirectResponse(
            url="/admin/login/2fa?notice=" + quote_plus("A new code has been sent."),
            status_code=302,
        )

    # ------------------------------------------------------------------
    # GET /verify-email — verification landing page
    # ------------------------------------------------------------------

    @get("/verify-email")
    async def verify_email_form(self, request: Request) -> HTMLResponse | RedirectResponse:
        """Display the standalone email verification landing page.

        Shown after a login attempt was gated on an unverified email.  Lets
        the admin request a fresh verification link.

        Args:
            request: Incoming HTTP request.

        Returns:
            HTMLResponse with the rendered page, or a RedirectResponse when
            already authenticated.
        """
        user = getattr(request.state, "user", None)
        if user and user.user_id != "guest":
            return RedirectResponse(url="/admin/", status_code=302)

        email = request.session.get("verify_pending_email", "")
        next_url = request.session.get("verify_pending_next", "/admin/")
        error = request.query_params.get("error", "")
        notice = request.query_params.get("notice", "")
        csrf_token = self._fresh_csrf(request)

        html = render_verify_email_page(
            email=email,
            error=error,
            notice=notice,
            csrf_token=csrf_token,
            next_url=next_url,
        )
        return HTMLResponse(content=html)

    # ------------------------------------------------------------------
    # POST /verify-email/resend — request a fresh verification link
    # ------------------------------------------------------------------

    @post("/verify-email/resend")
    async def verify_email_resend(self, request: Request) -> RedirectResponse:
        """Re-issue the verification email for a pending verification.

        Rate limited per IP (5/hour, fail open) by the verification service.

        Args:
            request: Incoming HTTP request carrying form data.

        Returns:
            RedirectResponse to /admin/verify-email with a notice on success
            or an error query parameter on failure.
        """
        form_data = await request.form()
        csrf_token = str(form_data.get("csrf_token", ""))
        csrf_session_id = request.session.get("csrf_session_id", "")
        if not csrf_session_id or not self._csrf_service.validate_token(
            csrf_session_id, csrf_token
        ):
            logger.warning(
                "auth.csrf_validation_failed", ip=self._get_client_ip(request)
            )
            return RedirectResponse(
                url=f"/admin/verify-email?error={quote_plus('Invalid or expired security token. Please try again.')}",
                status_code=302,
            )

        user_id = request.session.get("verify_pending_user_id", "")
        if not user_id:
            return RedirectResponse(
                url=f"/admin/login?error={quote_plus('Please sign in to request a new link.')}",
                status_code=302,
            )
        if self._email_verification_service is None:
            return RedirectResponse(
                url=f"/admin/verify-email?error={quote_plus('Email verification is not available.')}",
                status_code=302,
            )

        email = str(form_data.get("email", "")) or request.session.get(
            "verify_pending_email", ""
        )
        result = await self._email_verification_service.send_verification(
            user_id=user_id,
            email=email,
            user_name=email,
            base_url=str(request.base_url),
            ip_address=self._get_client_ip(request),
        )
        if result.is_err():
            return RedirectResponse(
                url=f"/admin/verify-email?error={quote_plus(str(result.unwrap_err()))}",
                status_code=302,
            )
        return RedirectResponse(
            url="/admin/verify-email?notice="
            + quote_plus("A new verification link has been sent."),
            status_code=302,
        )

    # ------------------------------------------------------------------
    # GET /verify-email/{token} — consume a verification link
    # ------------------------------------------------------------------

    @get("/verify-email/{token}")
    async def verify_email_token(self, request: Request) -> HTMLResponse:
        """Consume a verification token from an emailed link.

        Renders a confirmation page on success and a failure page (invalid,
        used, or expired token) otherwise.  No session is required.

        Args:
            request: Incoming HTTP request (``token`` from path params).

        Returns:
            HTMLResponse with the confirmation or failure page.
        """
        token = request.path_params.get("token", "")
        if self._email_verification_service is None:
            return HTMLResponse(
                content=render_email_verified_page(
                    error="Email verification is not available."
                )
            )

        result = await self._email_verification_service.verify_token(token)
        if result.is_err():
            logger.warning(
                "auth.verify_email_token_failed",
                token_prefix=token[:8],
                reason=str(result.unwrap_err()),
            )
            return HTMLResponse(
                content=render_email_verified_page(error=str(result.unwrap_err()))
            )

        for key in (
            "verify_pending_user_id",
            "verify_pending_email",
            "verify_pending_next",
        ):
            request.session.pop(key, None)
        logger.info("auth.verify_email_success", token_prefix=token[:8])
        return HTMLResponse(content=render_email_verified_page())

    # ------------------------------------------------------------------
    # GET /profile/mfa — self-service 2FA settings
    # ------------------------------------------------------------------

    @get("/profile/mfa")
    async def mfa_profile_form(self, request: Request) -> HTMLResponse | RedirectResponse:
        """Display the authenticated user's 2FA settings page.

        Shows the disable form when 2FA is active; otherwise generates a
        fresh secret, QR code, and confirm form.  Requires an authenticated
        request (``request.state.user`` provided by the auth guard).

        Args:
            request: Incoming HTTP request.

        Returns:
            HTMLResponse with the rendered setup page, or a RedirectResponse
            when unauthenticated or 2FA is disabled in configuration.
        """
        user = getattr(request.state, "user", None)
        if not user or user.user_id == "guest":
            return RedirectResponse(
                url="/admin/login?next=/admin/profile/mfa", status_code=302
            )
        if self._mfa_service is None:
            return RedirectResponse(url="/admin/", status_code=302)

        error = request.query_params.get("error", "")
        notice = request.query_params.get("notice", "")
        csrf_token = self._fresh_csrf(request)
        user_id = str(user.user_id)

        email_verified: bool | None = None
        if self._email_verification_service is not None:
            email_verified = await self._email_verification_service.is_verified(
                user_id
            )

        if await self._mfa_service.is_enabled(user_id):
            html = render_mfa_setup_page(
                enabled=True,
                error=error,
                notice=notice,
                csrf_token=csrf_token,
                email_verified=email_verified,
            )
        else:
            result = await self._mfa_service.start_setup(user_id, str(user.email))
            if result.is_err():
                html = render_mfa_setup_page(
                    enabled=False,
                    error=str(result.unwrap_err()),
                    csrf_token=csrf_token,
                    email_verified=email_verified,
                )
            else:
                secret, _, svg = result.unwrap()
                request.session["mfa_pending_secret"] = secret
                html = render_mfa_setup_page(
                    enabled=False,
                    qr_svg=svg,
                    secret=secret,
                    error=error,
                    notice=notice,
                    csrf_token=csrf_token,
                    email_verified=email_verified,
                )
        return HTMLResponse(content=html)

    # ------------------------------------------------------------------
    # POST /profile/mfa/setup — enable 2FA
    # ------------------------------------------------------------------

    @post("/profile/mfa/setup")
    async def mfa_setup_submit(self, request: Request) -> RedirectResponse:
        """Confirm a newly generated TOTP secret.

        Validates the code from the setup form against the pending secret
        stashed in the session; only a valid code persists the secret.

        Args:
            request: Incoming HTTP request carrying form data.

        Returns:
            RedirectResponse to /admin/profile/mfa with a notice on success
            or an error query parameter on failure.
        """
        user = getattr(request.state, "user", None)
        if not user or user.user_id == "guest":
            return RedirectResponse(
                url="/admin/login?next=/admin/profile/mfa", status_code=302
            )
        if self._mfa_service is None:
            return RedirectResponse(url="/admin/", status_code=302)

        form_data = await request.form()
        csrf_token = str(form_data.get("csrf_token", ""))
        csrf_session_id = request.session.get("csrf_session_id", "")
        if not csrf_session_id or not self._csrf_service.validate_token(
            csrf_session_id, csrf_token
        ):
            logger.warning(
                "auth.csrf_validation_failed", ip=self._get_client_ip(request)
            )
            return RedirectResponse(
                url=f"/admin/profile/mfa?error={quote_plus('Invalid or expired security token. Please try again.')}",
                status_code=302,
            )

        code = str(form_data.get("code", ""))
        secret = request.session.pop("mfa_pending_secret", "")
        if not code or not secret:
            return RedirectResponse(
                url=f"/admin/profile/mfa?error={quote_plus('Verification code is required.')}",
                status_code=302,
            )

        result = await self._mfa_service.confirm_setup(str(user.user_id), secret, code)
        if result.is_err():
            return RedirectResponse(
                url=f"/admin/profile/mfa?error={quote_plus(str(result.unwrap_err()))}",
                status_code=302,
            )
        return RedirectResponse(
            url="/admin/profile/mfa?notice="
            + quote_plus("Two-factor authentication enabled."),
            status_code=302,
        )

    # ------------------------------------------------------------------
    # POST /profile/mfa/disable — disable 2FA
    # ------------------------------------------------------------------

    @post("/profile/mfa/disable")
    async def mfa_disable_submit(self, request: Request) -> RedirectResponse:
        """Disable 2FA after validating the current TOTP code.

        Requires the user to prove possession of the secret by entering a
        valid current code.

        Args:
            request: Incoming HTTP request carrying form data.

        Returns:
            RedirectResponse to /admin/profile/mfa with a notice on success
            or an error query parameter on failure.
        """
        user = getattr(request.state, "user", None)
        if not user or user.user_id == "guest":
            return RedirectResponse(
                url="/admin/login?next=/admin/profile/mfa", status_code=302
            )
        if self._mfa_service is None:
            return RedirectResponse(url="/admin/", status_code=302)

        form_data = await request.form()
        csrf_token = str(form_data.get("csrf_token", ""))
        csrf_session_id = request.session.get("csrf_session_id", "")
        if not csrf_session_id or not self._csrf_service.validate_token(
            csrf_session_id, csrf_token
        ):
            logger.warning(
                "auth.csrf_validation_failed", ip=self._get_client_ip(request)
            )
            return RedirectResponse(
                url=f"/admin/profile/mfa?error={quote_plus('Invalid or expired security token. Please try again.')}",
                status_code=302,
            )

        code = str(form_data.get("code", ""))
        if not code:
            return RedirectResponse(
                url=f"/admin/profile/mfa?error={quote_plus('Verification code is required.')}",
                status_code=302,
            )

        result = await self._mfa_service.disable(str(user.user_id), code)
        if result.is_err():
            return RedirectResponse(
                url=f"/admin/profile/mfa?error={quote_plus(str(result.unwrap_err()))}",
                status_code=302,
            )
        request.session.pop("mfa_pending_secret", None)
        return RedirectResponse(
            url="/admin/profile/mfa?notice="
            + quote_plus("Two-factor authentication disabled."),
            status_code=302,
        )

    # ------------------------------------------------------------------
    # GET /password-reset — request form
    # ------------------------------------------------------------------

    @get("/password-reset")
    async def password_reset_request_form(
        self, request: Request
    ) -> HTMLResponse | RedirectResponse:
        """Display the standalone password reset request form.

        Redirects authenticated users to the admin home.  A fresh CSRF
        token is embedded for unauthenticated visitors.

        Args:
            request: Incoming HTTP request.

        Returns:
            HTMLResponse with the rendered request page, or a
            RedirectResponse when already authenticated.
        """
        user = getattr(request.state, "user", None)
        if user and user.user_id != "guest":
            return RedirectResponse(url="/admin/", status_code=302)

        error = request.query_params.get("error", "")
        sent = request.query_params.get("sent", "") == "1"

        csrf_session_id = secrets.token_urlsafe(16)
        request.session["csrf_session_id"] = csrf_session_id
        csrf_token = self._csrf_service.generate_token(csrf_session_id)

        html = render_password_reset_request_page(
            error=error, csrf_token=csrf_token, sent=sent
        )
        return HTMLResponse(content=html)

    # ------------------------------------------------------------------
    # POST /password-reset — request submit
    # ------------------------------------------------------------------

    @post("/password-reset")
    async def password_reset_request_submit(self, request: Request) -> RedirectResponse:
        """Process the password reset request form.

        Always redirects to the generic ``sent`` notice — the response is
        identical whether or not the email exists (anti-enumeration).

        Args:
            request: Incoming HTTP request carrying form data.

        Returns:
            RedirectResponse to the request page with ``sent=1``.
        """
        form_data = await request.form()
        email = str(form_data.get("email", ""))
        csrf_token = str(form_data.get("csrf_token", ""))

        csrf_session_id = request.session.get("csrf_session_id", "")
        if not csrf_session_id or not self._csrf_service.validate_token(
            csrf_session_id, csrf_token
        ):
            return RedirectResponse(
                url=f"/admin/password-reset?error={quote_plus('Invalid or expired security token. Please try again.')}",
                status_code=302,
            )

        if not email:
            return RedirectResponse(
                url=f"/admin/password-reset?error={quote_plus('Email is required.')}",
                status_code=302,
            )

        if self._password_reset_service is not None:
            result = await self._password_reset_service.request_reset(
                email=email,
                ip_address=self._get_client_ip(request),
                user_agent=request.headers.get("user-agent", ""),
                base_url=str(request.base_url),
            )
            if result.is_err():
                return RedirectResponse(
                    url=f"/admin/password-reset?error={quote_plus(str(result.unwrap_err()))}",
                    status_code=302,
                )
        return RedirectResponse(url="/admin/password-reset?sent=1", status_code=302)

    # ------------------------------------------------------------------
    # GET /password-reset/{token} — confirm form
    # ------------------------------------------------------------------

    @get("/password-reset/{token}")
    async def password_reset_confirm_form(
        self, request: Request
    ) -> HTMLResponse | RedirectResponse:
        """Display the standalone confirm form for a reset token.

        Args:
            request: Incoming HTTP request (``token`` from path params).

        Returns:
            HTMLResponse with the rendered confirm page, or a
            RedirectResponse when already authenticated.
        """
        user = getattr(request.state, "user", None)
        if user and user.user_id != "guest":
            return RedirectResponse(url="/admin/", status_code=302)

        token = request.path_params.get("token", "")
        error = request.query_params.get("error", "")

        csrf_session_id = secrets.token_urlsafe(16)
        request.session["csrf_session_id"] = csrf_session_id
        csrf_token = self._csrf_service.generate_token(csrf_session_id)

        html = render_password_reset_confirm_page(
            token=token, error=error, csrf_token=csrf_token
        )
        return HTMLResponse(content=html)

    # ------------------------------------------------------------------
    # POST /password-reset/{token} — confirm submit
    # ------------------------------------------------------------------

    @post("/password-reset/{token}")
    async def password_reset_confirm_submit(self, request: Request) -> RedirectResponse:
        """Process the new-password form.

        Validates CSRF and password/confirmation match, then delegates to
        the reset service.  On success the user is redirected to the login
        page with a success notice; on failure back to the confirm form
        with an error message.

        Args:
            request: Incoming HTTP request carrying form data.

        Returns:
            RedirectResponse to the login page or back to the confirm form.
        """
        token = request.path_params.get("token", "")
        form_data = await request.form()
        password = str(form_data.get("password", ""))
        password_confirmation = str(form_data.get("password_confirmation", ""))
        csrf_token = str(form_data.get("csrf_token", ""))

        csrf_session_id = request.session.get("csrf_session_id", "")
        if not csrf_session_id or not self._csrf_service.validate_token(
            csrf_session_id, csrf_token
        ):
            return RedirectResponse(
                url=f"/admin/password-reset/{token}?error={quote_plus('Invalid or expired security token. Please try again.')}",
                status_code=302,
            )

        if not password or password != password_confirmation:
            return RedirectResponse(
                url=f"/admin/password-reset/{token}?error={quote_plus('Passwords do not match.')}",
                status_code=302,
            )

        if self._password_reset_service is None:
            return RedirectResponse(
                url=f"/admin/password-reset/{token}?error={quote_plus('Password reset is not available.')}",
                status_code=302,
            )

        result = await self._password_reset_service.confirm_reset(
            token=token,
            new_password=password,
            ip_address=self._get_client_ip(request),
            user_agent=request.headers.get("user-agent", ""),
        )
        if result.is_ok():
            logger.info("admin.password_reset_confirm_success", token_prefix=token[:8])
            return RedirectResponse(
                url=f"/admin/login?notice={quote_plus('Password reset successful. Please sign in.')}",
                status_code=302,
            )

        logger.warning(
            "admin.password_reset_confirm_failed", error=str(result.unwrap_err())
        )
        return RedirectResponse(
            url=f"/admin/password-reset/{token}?error={quote_plus(str(result.unwrap_err()))}",
            status_code=302,
        )

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
