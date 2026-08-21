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
from lexigram.admin.lib.template import (
    render_email_verified_page,
    render_register_page,
    render_verify_email_page,
)
from lexigram.contracts.web import get, post

if TYPE_CHECKING:
    from lexigram.admin.auth.protocols import (
        AdminCsrfServiceProtocol,
        AdminEmailVerificationServiceProtocol,
    )
    from lexigram.admin.auth.store import AdminUserStoreProtocol


class AuthRegistrationMixin(AuthCoreMixin):
    """AuthController registration endpoints."""

    _csrf_service: AdminCsrfServiceProtocol
    _email_verification_service: AdminEmailVerificationServiceProtocol | None
    _user_store: AdminUserStoreProtocol | None
    _registration_default_role: str
    _registration_domains: list[str]
    _registration_enabled: bool

    @get("/register")
    async def register_form(self, request: Request) -> HTMLResponse | RedirectResponse:
        """Display the standalone registration page.

        Only reachable when self-service registration is enabled in
        configuration; already-authenticated users are redirected home.

        Args:
            request: Incoming HTTP request.

        Returns:
            HTMLResponse with the rendered registration page, or a
            RedirectResponse when registration is disabled or the user is
            already signed in.
        """
        if not self._registration_enabled or self._user_store is None:
            return RedirectResponse(
                url="/admin/login?error="
                + quote_plus("Registration is not available."),
                status_code=302,
            )
        error = _humanize_error(request.query_params.get("error", ""))
        notice = request.query_params.get("notice", "")
        user = getattr(request.state, "user", None)
        if user and user.user_id != "guest" and not error and not notice:
            return RedirectResponse(
                url="/admin/", status_code=302, headers=_CACHE_CONTROL_NO_STORE
            )

        name = request.query_params.get("name", "")
        email = request.query_params.get("email", "")
        csrf_token = self._fresh_csrf(request)

        html = render_register_page(
            error=error,
            notice=notice,
            csrf_token=csrf_token,
            name=name,
            email=email,
            name_err=request.query_params.get("name_err", ""),
            email_err=request.query_params.get("email_err", ""),
            password_err=request.query_params.get("password_err", ""),
            confirmation_err=request.query_params.get("confirmation_err", ""),
        )
        return HTMLResponse(content=html, headers=_CACHE_CONTROL_NO_STORE)

    @post("/register")
    async def register_submit(self, request: Request) -> RedirectResponse:
        """Process the registration form.

        Validates CSRF, required fields, password confirmation, and the
        configured email-domain allowlist, then persists the new account
        via the admin user store and signs the user in directly.

        Args:
            request: Incoming HTTP request carrying form data.

        Returns:
            RedirectResponse to /admin/ on success, or back to the
            registration page with an error query parameter.
        """
        if not self._registration_enabled or self._user_store is None:
            return RedirectResponse(
                url="/admin/login?error="
                + quote_plus("Registration is not available."),
                status_code=302,
            )

        form_data = request.scope.get("admin_form_data") or await request.form()
        name = str(form_data.get("name", "")).strip()
        email = str(form_data.get("email", "")).strip().lower()
        password = str(form_data.get("password", ""))
        password_confirmation = str(form_data.get("password_confirmation", ""))
        csrf_token = str(form_data.get("csrf_token", ""))

        csrf_session_id = request.session.get("csrf_session_id", "")
        if not csrf_session_id or not self._csrf_service.validate_token(
            csrf_session_id, csrf_token
        ):
            logger.warning(
                "auth.csrf_validation_failed", ip=self._get_client_ip(request)
            )
            return RedirectResponse(
                url=f"/admin/register?error={quote_plus('Invalid or expired security token. Please try again.')}",
                status_code=302,
            )

        if not name or not email or not password:
            name_err = "Name is required." if not name else ""
            email_err = "Email is required." if not email else ""
            password_err = "Password is required." if not password else ""
            params = [f"name={quote_plus(name)}", f"email={quote_plus(email)}"]
            if name_err:
                params.append(f"name_err={quote_plus(name_err)}")
            if email_err:
                params.append(f"email_err={quote_plus(email_err)}")
            if password_err:
                params.append(f"password_err={quote_plus(password_err)}")
            return RedirectResponse(
                url=f"/admin/register?{'&'.join(params)}",
                status_code=302,
            )

        if len(password) < 8:
            return RedirectResponse(
                url=f"/admin/register?error={quote_plus('Password must be at least 8 characters.')}&name={quote_plus(name)}&email={quote_plus(email)}&password_err={quote_plus('Password must be at least 8 characters.')}",
                status_code=302,
            )

        if password != password_confirmation:
            return RedirectResponse(
                url=f"/admin/register?error={quote_plus('Passwords do not match.')}&name={quote_plus(name)}&email={quote_plus(email)}&confirmation_err={quote_plus('Passwords do not match.')}",
                status_code=302,
            )

        if self._registration_domains and "@" in email:
            domain = email.rsplit("@", 1)[1]
            if domain not in self._registration_domains:
                return RedirectResponse(
                    url=f"/admin/register?error={quote_plus('Registration is restricted to allowed email domains.')}&name={quote_plus(name)}&email={quote_plus(email)}",
                    status_code=302,
                )

        existing = await self._user_store.get_user_by_email(email)
        if existing is not None:
            logger.info(
                "auth.register_duplicate_email",
                email=email,
                ip=self._get_client_ip(request),
            )
            return RedirectResponse(
                url=f"/admin/register?error={quote_plus('An account with this email already exists. Please log in instead.')}&name={quote_plus(name)}&email={quote_plus(email)}",
                status_code=302,
            )

        ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        from lexigram.admin.lib.password import hash_password

        hashed = hash_password(password)
        roles = (
            [self._registration_default_role]
            if self._registration_default_role
            else None
        )
        try:
            created = await self._user_store.create_user(
                name=name,
                email=email,
                hashed_password=hashed,
                roles=roles,
            )
        except Exception as exc:  # noqa: BLE001 — persistence failures surface to the user
            logger.warning(
                "auth.register_create_failed",
                email=email,
                ip=ip,
                error=str(exc),
            )
            return RedirectResponse(
                url=f"/admin/register?error={quote_plus('Could not create the account: email may already be in use.')}&name={quote_plus(name)}&email={quote_plus(email)}",
                status_code=302,
            )

        user_id = str(getattr(created, "user_id", "") or getattr(created, "id", ""))
        logger.info("auth.register_success", email=email, user_id=user_id)

        await self._audit_registration(request, ip, user_agent, email)

        notice = "Account created successfully — please sign in."
        if (
            self._email_verification_service is not None
            and user_id
            and await self._email_verification_service.is_required(user_id)
        ):
            verify_result = await self._email_verification_service.send_verification(
                user_id=user_id,
                email=email,
                user_name=name,
                base_url=str(request.base_url),
                ip_address=ip,
            )
            if verify_result.is_ok():
                notice = (
                    "Account created successfully — a verification email was "
                    f"sent to {email}. Please verify your email before "
                    "signing in."
                )
            else:
                logger.warning(
                    "auth.register_verification_send_failed",
                    email=email,
                    error=str(verify_result.unwrap_err()),
                )
                notice = (
                    "Account created successfully — email verification is "
                    "enabled, and you will be asked to verify your email "
                    "before signing in."
                )
        return RedirectResponse(
            url="/admin/login?notice=" + quote_plus(notice),
            status_code=302,
        )

    async def _audit_registration(
        self, request: Request, ip_address: str, user_agent: str, email: str
    ) -> None:
        """Record the registration audit event (best-effort).

        Resolves the audit service from the request DI container, mirroring
        the theme-overrides pattern; failures are logged, never raised.

        Args:
            request: The current request (carries the DI container).
            ip_address: Client IP for the audit record.
            user_agent: Client user agent for the audit record.
            email: Registered email address.
        """
        try:
            from lexigram.admin.auth.protocols import AdminAuditLogServiceProtocol
            from lexigram.admin.auth.types import AdminSecurityEventType

            container = getattr(request.state, "container", None)
            if container is None:
                return
            audit_service = await container.resolve(
                AdminAuditLogServiceProtocol,
                bypass_visibility=True,
            )
            await audit_service.log_event(
                event_type=AdminSecurityEventType.USER_REGISTERED,
                ip_address=ip_address,
                user_agent=user_agent,
                success=True,
                metadata={"email": email},
            )
        except Exception as exc:  # noqa: BLE001 — auditing is best-effort
            logger.warning("auth.register_audit_failed", error=str(exc))

    @get("/verify-email")
    async def verify_email_form(
        self, request: Request
    ) -> HTMLResponse | RedirectResponse:
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
        error = _humanize_error(request.query_params.get("error", ""))
        notice = request.query_params.get("notice", "")
        csrf_token = self._fresh_csrf(request)

        html = render_verify_email_page(
            email=email,
            error=error,
            notice=notice,
            csrf_token=csrf_token,
            next_url=next_url,
        )
        return HTMLResponse(content=html, headers=_CACHE_CONTROL_NO_STORE)

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
                url=f"/admin/verify-email?error={quote_plus(_humanize_error(str(result.unwrap_err())))}",
                status_code=302,
            )
        return RedirectResponse(
            url="/admin/verify-email?notice="
            + quote_plus("A new verification link has been sent."),
            status_code=302,
        )

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
                content=render_email_verified_page(
                    error=_humanize_error(str(result.unwrap_err()))
                )
            )

        for key in (
            "verify_pending_user_id",
            "verify_pending_email",
            "verify_pending_next",
        ):
            request.session.pop(key, None)
        logger.info("auth.verify_email_success", token_prefix=token[:8])
        return HTMLResponse(content=render_email_verified_page())
