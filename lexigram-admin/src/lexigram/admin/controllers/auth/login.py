from __future__ import annotations

import secrets
from typing import TYPE_CHECKING
from urllib.parse import quote_plus

from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse

from lexigram.admin.controllers.auth.core import (
    _CACHE_CONTROL_NO_STORE,
    _humanize_error,
    logger,
)
from lexigram.admin.lib.template import render_login_page
from lexigram.contracts.web import get, post

if TYPE_CHECKING:
    from lexigram.admin.auth.protocols import (
        AdminAuthServiceProtocol,
        AdminCsrfServiceProtocol,
        AdminEmailOtpServiceProtocol,
        AdminEmailVerificationServiceProtocol,
        AdminMfaServiceProtocol,
    )
    from lexigram.admin.observability.admin_metrics import AdminMetrics


class AuthLoginMixin:
    """AuthController login endpoints."""

    @staticmethod
    def _safe_next_url(candidate: str) -> str:
        raise NotImplementedError

    def _get_client_ip(self, request: Request) -> str:
        raise NotImplementedError

    _auth_service: AdminAuthServiceProtocol
    _csrf_service: AdminCsrfServiceProtocol
    _email_otp_service: AdminEmailOtpServiceProtocol | None
    _email_verification_service: AdminEmailVerificationServiceProtocol | None
    _metrics: AdminMetrics
    _mfa_service: AdminMfaServiceProtocol | None
    _registration_enabled: bool

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
        next_url = self._safe_next_url(request.query_params.get("next", "/admin/"))

        error = _humanize_error(request.query_params.get("error", ""))
        notice = request.query_params.get("notice", "")
        email_err = request.query_params.get("email_err", "")
        password_err = request.query_params.get("password_err", "")

        user = getattr(request.state, "user", None)
        if user and user.user_id != "guest" and not error and not notice:
            return RedirectResponse(
                url=self._safe_next_url(next_url),
                status_code=302,
                headers=_CACHE_CONTROL_NO_STORE,
            )

        csrf_session_id = secrets.token_urlsafe(16)
        request.session["csrf_session_id"] = csrf_session_id
        csrf_token = self._csrf_service.generate_token(csrf_session_id)

        html = render_login_page(
            next_url=next_url,
            error=error,
            csrf_token=csrf_token,
            notice=notice,
            registration_enabled=self._registration_enabled,
            email_err=email_err,
            password_err=password_err,
        )
        return HTMLResponse(content=html, headers=_CACHE_CONTROL_NO_STORE)

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
        form_data = request.scope.get("admin_form_data") or await request.form()
        email = str(form_data.get("email", ""))
        password = str(form_data.get("password", ""))
        next_url = self._safe_next_url(str(form_data.get("next", "/admin/")))
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
            email_err = "Email is required." if not email else ""
            password_err = "Password is required." if not password else ""
            params = [f"next={quote_plus(next_url)}"]
            if email_err:
                params.append(f"email_err={quote_plus(email_err)}")
            if password_err:
                params.append(f"password_err={quote_plus(password_err)}")
            return RedirectResponse(
                url=f"/admin/login?{'&'.join(params)}",
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
                    factor = self._mfa_service.get_factor()
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
                error_msg = ""
                if self._email_verification_service is not None:
                    verify_result = (
                        await self._email_verification_service.send_verification(
                            user_id=auth_result.user_id,
                            email=auth_result.email,
                            user_name=auth_result.email,
                            base_url=str(request.base_url),
                            ip_address=ip,
                        )
                    )
                    if verify_result.is_err():
                        error_msg = str(verify_result.unwrap_err())
                        logger.error(
                            "auth.login_verification_send_failed",
                            user_id=auth_result.user_id,
                            reason=error_msg,
                        )
                logger.info(
                    "auth.login_verification_required",
                    user_id=auth_result.user_id,
                    email=auth_result.email,
                )
                target = "/admin/verify-email"
                if error_msg:
                    target += f"?error={quote_plus(error_msg)}"
                return RedirectResponse(url=target, status_code=302)

            request.session["admin_user_id"] = auth_result.user_id
            request.session["admin_user_email"] = auth_result.email
            request.session["admin_session_expires_at"] = (
                auth_result.expires_at.isoformat()
            )
            request.session.pop("csrf_session_id", None)
            if hasattr(auth_result, "session_id"):
                request.session["session_id"] = auth_result.session_id
            self._metrics.record_login(status="success")
            logger.info(
                "auth.login_success",
                user_id=auth_result.user_id,
                email=auth_result.email,
                redirect=next_url,
            )
            from lexigram.admin.state.context import AdminContextManager

            async with AdminContextManager(request) as ctx:
                ctx.add_flash("Signed in successfully.", "success")
            return RedirectResponse(url=self._safe_next_url(next_url), status_code=302)

        error_msg = _humanize_error(str(result.unwrap_err()))
        self._metrics.record_login(status="failure")
        logger.warning("auth.login_failed", email=email, ip=ip, reason=error_msg)
        return RedirectResponse(
            url=f"/admin/login?error={quote_plus(error_msg)}&next={quote_plus(next_url)}",
            status_code=302,
        )

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
        return RedirectResponse(
            url="/admin/login?notice=" + quote_plus("You have been signed out."),
            status_code=302,
        )
