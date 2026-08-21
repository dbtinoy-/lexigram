from __future__ import annotations

import secrets
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
from lexigram.admin.lib.template import (
    render_password_reset_confirm_page,
    render_password_reset_request_page,
)
from lexigram.contracts.web import get, post

if TYPE_CHECKING:
    from lexigram.admin.auth.protocols import (
        AdminCsrfServiceProtocol,
        AdminPasswordResetServiceProtocol,
    )


class AuthPasswordResetMixin(AuthCoreMixin):
    """AuthController password_reset endpoints."""

    _csrf_service: AdminCsrfServiceProtocol
    _password_reset_service: AdminPasswordResetServiceProtocol | None

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
        return HTMLResponse(content=html, headers=_CACHE_CONTROL_NO_STORE)

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
        form_data = request.scope.get("admin_form_data") or await request.form()
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
                    url=f"/admin/password-reset?error={quote_plus(_humanize_error(str(result.unwrap_err())))}",
                    status_code=302,
                )
        return RedirectResponse(url="/admin/password-reset?sent=1", status_code=302)

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
            token=token,
            error=error,
            csrf_token=csrf_token,
            password_err=request.query_params.get("password_err", ""),
            confirmation_err=request.query_params.get("confirmation_err", ""),
        )
        return HTMLResponse(content=html, headers=_CACHE_CONTROL_NO_STORE)

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
        form_data = request.scope.get("admin_form_data") or await request.form()
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

        if not password or not password_confirmation:
            password_err = "New password is required." if not password else ""
            confirmation_err = (
                "Please confirm your password." if not password_confirmation else ""
            )
            return RedirectResponse(
                url=f"/admin/password-reset/{token}?password_err={quote_plus(password_err)}&confirmation_err={quote_plus(confirmation_err)}",
                status_code=302,
            )

        if password != password_confirmation:
            return RedirectResponse(
                url=f"/admin/password-reset/{token}?confirmation_err={quote_plus('Passwords do not match.')}",
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
            url=f"/admin/password-reset/{token}?error={quote_plus(_humanize_error(str(result.unwrap_err())))}",
            status_code=302,
        )
