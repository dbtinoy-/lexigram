"""Session/token lifecycle for the admin authentication flow.

Encapsulates post-credential session issuance (attempt recording,
lockout clearance, session creation, and the paired audit events) plus
session revocation, consumed by
:class:`lexigram.admin.auth.services.auth_service.AdminAuthService`.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from lexigram.admin.auth.protocols import (
    AdminAuditLogServiceProtocol,
    AdminLoginAttemptServiceProtocol,
    AdminSessionServiceProtocol,
)
from lexigram.admin.auth.types import AdminSecurityEventType
from lexigram.logging import get_logger

logger = get_logger(__name__)


class SessionLifecycleCoordinator:
    """Issues and revokes admin sessions with their audit trail.

    Args:
        attempt_service: IP rate limiting and lockout enforcement.
        session_service: Session lifecycle management.
        audit_service: Security event recording (fire-and-forget).
        session_lifetime: Absolute session TTL in seconds.
    """

    def __init__(
        self,
        attempt_service: AdminLoginAttemptServiceProtocol,
        session_service: AdminSessionServiceProtocol,
        audit_service: AdminAuditLogServiceProtocol,
        session_lifetime: int = 86400,
    ) -> None:
        self._attempt_service = attempt_service
        self._session_service = session_service
        self._audit_service = audit_service
        self._session_lifetime = session_lifetime

    async def finalize_login(
        self,
        *,
        user_id: str,
        email: str,
        roles: list[str],
        ip_address: str,
        user_agent: str,
    ) -> tuple[str, datetime]:
        """Record login success, create the session, and emit its audits.

        Runs the shared tail of both login paths: attempt recording and
        lockout clearance, session creation, the ``SESSION_CREATED`` and
        ``LOGIN_SUCCESS`` audit events, and the ``admin_login_success``
        log line.

        Args:
            user_id: Admin user UUID.
            email: Admin user email.
            roles: Role names granted to the session.
            ip_address: Client IP address used for the session and audits.
            user_agent: Client user-agent string.

        Returns:
            Tuple of the new ``session_id`` and the absolute ``expires_at``.
        """
        # Step — Record success and clear lockout
        await self._attempt_service.record_attempt(
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
            success=True,
        )
        await self._attempt_service.clear_lockout(email)

        # Step — Create session
        session_id: str = await self._session_service.create_session(
            user_id=user_id,
            email=email,
            roles=roles,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self._audit_service.log_event(
            event_type=AdminSecurityEventType.SESSION_CREATED,
            ip_address=ip_address,
            user_agent=user_agent,
            success=True,
            admin_user_id=user_id,
            metadata={"email": email, "session_id": session_id},
        )

        expires_at: datetime = datetime.now(UTC) + timedelta(
            seconds=self._session_lifetime
        )

        # Step — Audit success
        await self._audit_service.log_event(
            event_type=AdminSecurityEventType.LOGIN_SUCCESS,
            ip_address=ip_address,
            user_agent=user_agent,
            success=True,
            admin_user_id=user_id,
            metadata={"email": email, "session_id": session_id},
        )
        logger.info(
            "admin_login_success",
            user_id=user_id,
            email=email,
            ip_address=ip_address,
        )
        return session_id, expires_at

    async def invalidate_session(self, session_id: str) -> None:
        """Revoke a single session (logout) with a ``LOGOUT`` audit event.

        Args:
            session_id: Identifier of the session to revoke.
        """
        await self._session_service.revoke_session(session_id)
        await self._audit_service.log_event(
            event_type=AdminSecurityEventType.LOGOUT,
            ip_address="",
            user_agent="",
            success=True,
            metadata={"session_id": session_id},
        )
        logger.info("admin_session_invalidated", session_id=session_id)

    async def invalidate_all_user_sessions(self, user_id: str) -> None:
        """Revoke all active sessions for an admin user.

        Called after a password change or administrative action requiring
        full session teardown. Emits a ``SESSION_REVOKED`` audit event.

        Args:
            user_id: UUID of the admin user whose sessions to revoke.
        """
        await self._session_service.revoke_all_user_sessions(user_id)
        await self._audit_service.log_event(
            event_type=AdminSecurityEventType.SESSION_REVOKED,
            ip_address="",
            user_agent="",
            success=True,
            admin_user_id=user_id,
            metadata={"reason": "all_sessions_revoked"},
        )
        logger.info("admin_all_sessions_invalidated", user_id=user_id)


__all__ = ["SessionLifecycleCoordinator"]
