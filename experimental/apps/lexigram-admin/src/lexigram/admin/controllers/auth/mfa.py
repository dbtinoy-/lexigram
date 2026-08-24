from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import quote_plus

from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse

from lexigram.admin.controllers.auth.core import (
    _CACHE_CONTROL_NO_STORE,
    AuthCoreMixin,
    _humanize_error,
    logger,
)
from lexigram.admin.lib.template import render_mfa_challenge_page, render_mfa_setup_page
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


class AuthMfaMixin(AuthCoreMixin):
    """AuthController mfa endpoints."""

    _auth_service: AdminAuthServiceProtocol
    _csrf_service: AdminCsrfServiceProtocol
    _email_otp_service: AdminEmailOtpServiceProtocol | None
    _email_verification_service: AdminEmailVerificationServiceProtocol | None
    _metrics: AdminMetrics
    _mfa_service: AdminMfaServiceProtocol | None

    @get("/login/2fa")
    async def mfa_challenge_form(
        self, request: Request
    ) -> HTMLResponse | RedirectResponse:
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
        error = _humanize_error(request.query_params.get("error", ""))
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
        return HTMLResponse(content=html, headers=_CACHE_CONTROL_NO_STORE)

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
        form_data = request.scope.get("admin_form_data") or await request.form()
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
        request.session["admin_session_expires_at"] = auth_result.expires_at.isoformat()
        request.session["session_id"] = auth_result.session_id
        request.session.pop("csrf_session_id", None)
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
        return RedirectResponse(url=self._safe_next_url(next_url), status_code=302)

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

        form_data = request.scope.get("admin_form_data") or await request.form()
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
                url=f"/admin/login/2fa?error={quote_plus(_humanize_error(str(result.unwrap_err())))}",
                status_code=302,
            )
        return RedirectResponse(
            url="/admin/login/2fa?notice=" + quote_plus("A new code has been sent."),
            status_code=302,
        )

    @get("/profile/mfa")
    async def mfa_profile_form(
        self, request: Request
    ) -> HTMLResponse | RedirectResponse:
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

        error = _humanize_error(request.query_params.get("error", ""))
        notice = request.query_params.get("notice", "")
        csrf_token = self._fresh_csrf(request)
        user_id = str(user.user_id)

        email_verified: bool | None = None
        if self._email_verification_service is not None:
            email_verified = await self._email_verification_service.is_verified(user_id)

        if await self._mfa_service.is_enabled(user_id):
            html = render_mfa_setup_page(
                enabled=True,
                csrf_token=csrf_token,
                email_verified=email_verified,
            )
        else:
            result = await self._mfa_service.start_setup(user_id, str(user.email))
            if result.is_err():
                error = _humanize_error(str(result.unwrap_err()))
                html = render_mfa_setup_page(
                    enabled=False,
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
                    csrf_token=csrf_token,
                    email_verified=email_verified,
                )

        from lexigram.admin.state.context import AdminContextManager

        async with AdminContextManager(request) as ctx:
            if error:
                ctx.add_flash(error, "error")
            if notice:
                ctx.add_flash(notice, "success")
            response = await self.render_admin(
                request,
                html,
                title="Two-Factor Authentication",
                breadcrumbs=self.generate_breadcrumbs(
                    ("Home", "/admin/"),
                    ("Profile", "/admin/profile"),
                    current="Two-Factor Authentication",
                ),
            )
        response.headers.update(_CACHE_CONTROL_NO_STORE)
        return response

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

        form_data = request.scope.get("admin_form_data") or await request.form()
        csrf_token = str(form_data.get("csrf_token", ""))
        csrf_session_id = request.session.get("csrf_session_id") or request.session.get(
            "admin_user_id", ""
        )
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
                url=f"/admin/profile/mfa?error={quote_plus(_humanize_error(str(result.unwrap_err())))}",
                status_code=302,
            )
        return RedirectResponse(
            url="/admin/profile/mfa?notice="
            + quote_plus("Two-factor authentication enabled."),
            status_code=302,
        )

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

        form_data = request.scope.get("admin_form_data") or await request.form()
        csrf_token = str(form_data.get("csrf_token", ""))
        csrf_session_id = request.session.get("csrf_session_id") or request.session.get(
            "admin_user_id", ""
        )
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
                url=f"/admin/profile/mfa?error={quote_plus(_humanize_error(str(result.unwrap_err())))}",
                status_code=302,
            )
        request.session.pop("mfa_pending_secret", None)
        return RedirectResponse(
            url="/admin/profile/mfa?notice="
            + quote_plus("Two-factor authentication disabled."),
            status_code=302,
        )
