"""Pre-login security gates for the admin authentication flow.

Encapsulates the IP rate-limit and account-lockout checks (with their
failure-path attempt recording and audit emission) consumed by
:class:`lexigram.admin.auth.services.auth_service.AdminAuthService`.
"""

from __future__ import annotations

from lexigram.admin.auth.errors import (
    AccountLockedError,
    RateLimitExceededError,
)
from lexigram.admin.auth.protocols import (
    AdminAuditLogServiceProtocol,
    AdminLoginAttemptServiceProtocol,
)
from lexigram.admin.auth.types import AdminSecurityEventType
from lexigram.logging import get_logger

logger = get_logger(__name__)


class LoginGuardPipeline:
    """Runs the pre-credential security gates and records blocked logins.

    Args:
        attempt_service: IP rate limiting and lockout enforcement.
        audit_service: Security event recording (fire-and-forget).
    """

    def __init__(
        self,
        attempt_service: AdminLoginAttemptServiceProtocol,
        audit_service: AdminAuditLogServiceProtocol,
    ) -> None:
        self._attempt_service = attempt_service
        self._audit_service = audit_service

    async def check_ip_rate_limit(
        self,
        *,
        email: str,
        ip_address: str,
        user_agent: str,
        failure_reason: str,
        extra_metadata: dict[str, str] | None = None,
        warn: bool = True,
    ) -> RateLimitExceededError | None:
        """Enforce the per-origin IP rate limit.

        On violation, records the failed attempt and emits a
        ``LOGIN_BLOCKED_IP`` audit event before returning the error.

        Args:
            email: Email involved in the attempted login.
            ip_address: Client IP address.
            user_agent: Client user-agent string.
            failure_reason: Reason recorded on the failed attempt.
            extra_metadata: Extra fields merged into the audit metadata.
            warn: Whether to emit the ``admin_login_blocked_ip`` warning log.

        Returns:
            The raised ``RateLimitExceededError`` when blocked, else ``None``.
        """
        try:
            await self._attempt_service.check_ip_rate_limit(ip_address)
        except RateLimitExceededError as exc:
            await self._attempt_service.record_attempt(
                email=email,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                failure_reason=failure_reason,
            )
            metadata: dict[str, str] = {"email": email}
            if extra_metadata:
                metadata.update(extra_metadata)
            await self._audit_service.log_event(
                event_type=AdminSecurityEventType.LOGIN_BLOCKED_IP,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                metadata=metadata,
            )
            if warn:
                logger.warning(
                    "admin_login_blocked_ip",
                    ip_address=ip_address,
                    email=email,
                )
            return exc
        return None

    async def check_account_lockout(
        self,
        *,
        email: str,
        ip_address: str,
        user_agent: str,
        extra_metadata: dict[str, str] | None = None,
        warn: bool = True,
    ) -> AccountLockedError | None:
        """Enforce the per-account lockout window.

        On violation, emits a ``LOGIN_BLOCKED_LOCKOUT`` audit event before
        returning the error.

        Args:
            email: Email involved in the attempted login.
            ip_address: Client IP address.
            user_agent: Client user-agent string.
            extra_metadata: Extra fields merged into the audit metadata.
            warn: Whether to emit the ``admin_login_blocked_lockout`` warning log.

        Returns:
            The raised ``AccountLockedError`` when locked, else ``None``.
        """
        try:
            await self._attempt_service.check_account_lockout(email)
        except AccountLockedError as exc:
            metadata: dict[str, str] = {"email": email}
            if extra_metadata:
                metadata.update(extra_metadata)
            await self._audit_service.log_event(
                event_type=AdminSecurityEventType.LOGIN_BLOCKED_LOCKOUT,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                metadata=metadata,
            )
            if warn:
                logger.warning(
                    "admin_login_blocked_lockout",
                    email=email,
                    ip_address=ip_address,
                )
            return exc
        return None


__all__ = ["LoginGuardPipeline"]
