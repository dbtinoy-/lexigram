"""Delegating auth adapter — wraps lexigram-auth services for admin use.

This adapter implements the same auth patterns admin currently uses
(``authenticate_admin``, ``resolve_admin_user``, session lifecycle) but
delegates the heavy lifting to ``lexigram.auth``'s ``AuthenticationService``
and ``SessionCookieBackend``.

Admin-specific concerns (rate limiting, lockout, audit logging) that live
outside lexigram-auth are handled through injected protocol implementations
passed to this adapter, ensuring the adapter itself has no direct dependency
on admin-internal services.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from starlette.requests import Request as StarletteRequest
from starlette.types import Scope

from lexigram.admin.auth.errors import (
    AccountLockedError,
    AdminAuthError,
    InvalidCredentialsError,
    RateLimitExceededError,
)
from lexigram.admin.auth.integration import AdminUser
from lexigram.contracts import AuthenticatedUserProtocol
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Protocols for capabilities we delegate INTO admin's existing services
# ---------------------------------------------------------------------------


class AdminRateLimiterProtocol(Protocol):
    """Enforces IP-based rate limiting for admin logins."""

    async def check_ip_rate_limit(self, ip_address: str) -> None: ...
    async def record_attempt(
        self, email: str, ip_address: str, success: bool, **metadata: Any
    ) -> None: ...


class AdminLockoutProtocol(Protocol):
    """Enforces per-account lockout for admin logins."""

    async def check_account_lockout(self, email: str) -> None: ...
    async def clear_lockout(self, email: str) -> None: ...


class AdminAuditProtocol(Protocol):
    """Records admin security events (fire-and-forget)."""

    async def log_login_success(
        self, user_id: str, email: str, ip_address: str, **metadata: Any
    ) -> None: ...
    async def log_login_failure(
        self, email: str, ip_address: str, reason: str, **metadata: Any
    ) -> None: ...
    async def log_logout(self, session_id: str, user_id: str | None = None) -> None: ...


# ---------------------------------------------------------------------------
# Wrapper types for auth results
# ---------------------------------------------------------------------------


@dataclass
class AdminAuthResult:
    """Result of a successful admin authentication."""

    user: AdminUser
    session_id: str
    expires_at: datetime


# ---------------------------------------------------------------------------
# The adapter
# ---------------------------------------------------------------------------


class DelegatingAuthAdapter:
    """Wraps lexigram-auth services for admin authentication and session mgmt.

    This adapter is the bridge between admin's security pipeline and the
    framework's canonical auth services.  Admin-internal concerns (rate
    limiting, lockout, auditing) are handled through injected admin
    protocol implementations, while credential verification and session
    lifecycle are delegated to lexigram-auth.

    The adapter is designed for construction via DI::

        adapter = DelegatingAuthAdapter(
            auth_service=authentication_service,
            cookie_backend=session_cookie_backend,
            rate_limiter=admin_rate_limiter,
            lockout=admin_lockout_service,
            audit=admin_audit_service,
        )
        result = await adapter.authenticate_admin("admin@x.com", "pw", "127.0.0.1")
    """

    def __init__(
        self,
        auth_service: object | None = None,
        cookie_backend: object | None = None,
        rate_limiter: AdminRateLimiterProtocol | None = None,
        lockout: AdminLockoutProtocol | None = None,
        audit: AdminAuditProtocol | None = None,
        session_lifetime: int = 86400,
    ) -> None:
        self._auth_service = auth_service
        self._cookie_backend = cookie_backend
        self._rate_limiter = rate_limiter
        self._lockout = lockout
        self._audit = audit
        self._session_lifetime = session_lifetime

    async def authenticate_admin(
        self,
        email: str,
        password: str,
        ip_address: str,
        user_agent: str = "",
    ) -> Result[AdminAuthResult, AdminAuthError]:
        """Authenticate an admin user via lexigram-auth.

        Pipeline:
        1. IP rate-limit check (admin concern).
        2. Account lockout check (admin concern).
        3. Credential verification via ``AuthenticationService.authenticate_user``.
        4. Clear lockout on success.
        5. Create session via ``SessionCookieBackend.login``.
        6. Audit logging (admin concern).

        Returns:
            ``Ok(AdminAuthResult)`` on success, or ``Err(AdminAuthError)``
            when rate-limited, locked out, or credentials are invalid.
        """
        # Step 1 — IP rate limit
        if self._rate_limiter is not None:
            try:
                await self._rate_limiter.check_ip_rate_limit(ip_address)
            except RateLimitExceededError as exc:
                if self._audit is not None:
                    await self._audit.log_login_failure(
                        email=email,
                        ip_address=ip_address,
                        reason="ip_rate_limited",
                    )
                logger.warning(
                    "admin_auth_ip_rate_limited",
                    ip_address=ip_address,
                    email=email,
                )
                return Err(exc)

        # Step 2 — Account lockout
        if self._lockout is not None:
            try:
                await self._lockout.check_account_lockout(email)
            except AccountLockedError as exc:
                if self._audit is not None:
                    await self._audit.log_login_failure(
                        email=email,
                        ip_address=ip_address,
                        reason="account_locked",
                    )
                logger.warning(
                    "admin_auth_account_locked",
                    email=email,
                    ip_address=ip_address,
                )
                return Err(exc)

        # Step 3 — Credential verification via lexigram-auth
        if self._auth_service is None:
            return Err(AdminAuthError("Authentication service unavailable"))
        result = await self._auth_service.authenticate_user(email, password)  # type: ignore[attr-defined]
        if result.is_err():
            if self._audit is not None:
                await self._audit.log_login_failure(
                    email=email,
                    ip_address=ip_address,
                    reason="invalid_credentials",
                )
            logger.info("admin_auth_failure", email=email, ip_address=ip_address)
            return Err(InvalidCredentialsError("Invalid email or password."))

        framework_user: AuthenticatedUserProtocol = result.unwrap()

        # Step 4 — Clear lockout on success
        if self._lockout is not None:
            await self._lockout.clear_lockout(email)

        # Step 5 — Wrap framework user in AdminUser (AUTH-11: delegate, not copy)
        admin_user = AdminUser(
            id=framework_user.user_id,
            email=framework_user.email,
            name=framework_user.name,
            framework_user=framework_user,
        )

        # Step 6 — Audit success
        if self._audit is not None:
            await self._audit.log_login_success(
                user_id=framework_user.user_id,
                email=framework_user.email,
                ip_address=ip_address,
            )

        logger.info(
            "admin_auth_success",
            user_id=framework_user.user_id,
            email=framework_user.email,
        )

        expires_at = datetime.now(UTC) + timedelta(seconds=self._session_lifetime)

        return Ok(
            AdminAuthResult(
                user=admin_user,
                session_id=framework_user.user_id,
                expires_at=expires_at,
            )
        )

    async def login(self, response: Any, user_id: str, expires_in: int = 86400) -> str:
        """Set a session cookie on the HTTP response.

        Delegates to ``SessionCookieBackend.login``.

        Args:
            response: Starlette ``Response`` to set cookie on.
            user_id: User identifier to associate with the session.
            expires_in: Session TTL in seconds.

        Returns:
            The created ``session_id``.
        """
        return await self._cookie_backend.login(response, user_id, expires_in)  # type: ignore[union-attr]

    async def logout(self, request: Any, response: Any) -> None:
        """Revoke the session and clear the cookie.

        Delegates to ``SessionCookieBackend.logout``.

        Args:
            request: Incoming ``Request`` containing the session cookie.
            response: Outgoing ``Response`` to clear the cookie on.
        """
        await self._cookie_backend.logout(request, response)  # type: ignore[union-attr]

        if self._audit is not None:
            session_id = request.cookies.get(
                getattr(self._cookie_backend, "cookie_name", "session_id")
            )
            await self._audit.log_logout(
                session_id=session_id or "unknown",
            )

    async def resolve_admin_user(self, request: Any) -> AdminUser | None:
        """Resolve the currently authenticated admin user from a request.

        Reads the session cookie, validates the session via
        ``SessionCookieBackend.authenticate``, and wraps the framework user
        in an ``AdminUser`` with delegation enabled.

        Args:
            request: The incoming Starlette ``Request``.

        Returns:
            An ``AdminUser`` with ``framework_user`` set, or ``None``.
        """
        framework_user = await self._cookie_backend.authenticate(request)  # type: ignore[union-attr]
        if framework_user is None:
            return None

        return self._wrap_framework_user(framework_user)

    async def resolve_admin_user_from_scope(self, scope: Scope) -> AdminUser | None:
        """Resolve the authenticated admin user from an ASGI scope.

        Lightweight variant of :meth:`resolve_admin_user` that builds a
        minimal Starlette ``Request`` from the raw ASGI scope so that
        ``AdminAuthGuardMiddleware`` can call it without the overhead of
        constructing a full Request object.

        Args:
            scope: ASGI connection scope (``type == "http"``).

        Returns:
            An ``AdminUser`` with ``framework_user`` set, or ``None``.
        """
        if scope.get("type") != "http":
            return None

        request = StarletteRequest(scope)
        return await self.resolve_admin_user(request)

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _wrap_framework_user(user: AuthenticatedUserProtocol) -> AdminUser:
        """Wrap a framework ``AuthenticatedUserProtocol`` in an ``AdminUser``.

        Properties are delegated through ``framework_user`` (AUTH-11) instead
        of being eagerly copied from the source.
        """
        return AdminUser(
            id=user.user_id,
            email=user.email,
            name=user.name,
            framework_user=user,
        )


__all__ = [
    "AdminAuditProtocol",
    "AdminAuthResult",
    "AdminLockoutProtocol",
    "AdminRateLimiterProtocol",
    "DelegatingAuthAdapter",
]
