"""Admin authentication orchestrator service.

Coordinates the complete login flow: IP rate limiting, account lockout,
credential verification, session issuance, and audit logging.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from lexigram.admin.auth.errors import (
    AccountLockedError,
    AdminAuthError,
    InvalidCredentialsError,
    MfaNotEnabledError,
    MfaVerificationFailedError,
    RateLimitExceededError,
)
from lexigram.admin.auth.protocols import (
    AdminAuditLogServiceProtocol,
    AdminLoginAttemptServiceProtocol,
    AdminMfaServiceProtocol,
    AdminSessionServiceProtocol,
)
from lexigram.admin.auth.store.protocols import AdminUserStoreProtocol
from lexigram.admin.auth.types import AdminAuthResult, AdminSecurityEventType
from lexigram.di.decorators import inject
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result

logger = get_logger(__name__)


@inject
class AdminAuthService:
    """Top-level authentication orchestrator for the admin panel.

    Coordinates the full login pipeline in strict order:

    1. IP rate-limit check — blocks brute-force by origin.
    2. Account lockout check — blocks repeated per-account failures.
    3. Credential verification — validates email/password.
    4. Attempt recording + lockout clearance on success.
    5. Session creation.
    6. Audit logging.

    All audit calls use ``AdminAuditLogServiceProtocol``, whose implementations
    are guaranteed never to raise; audit failures are silently absorbed so they
    never interrupt the authentication response.

    Args:
        user_store: Admin user persistence and credential verification.
        attempt_service: IP rate limiting and account lockout enforcement.
        audit_service: Security event recording (fire-and-forget).
        session_service: Session lifecycle management.
        mfa_service: Optional TOTP 2FA challenge service (None disables 2FA).
        session_lifetime: Absolute session TTL in seconds (default 86400 = 24h).
    """

    def __init__(
        self,
        user_store: AdminUserStoreProtocol,
        attempt_service: AdminLoginAttemptServiceProtocol,
        audit_service: AdminAuditLogServiceProtocol,
        session_service: AdminSessionServiceProtocol,
        mfa_service: AdminMfaServiceProtocol | None = None,
        session_lifetime: int = 86400,
    ) -> None:
        self._user_store = user_store
        self._attempt_service = attempt_service
        self._audit_service = audit_service
        self._session_service = session_service
        self._mfa_service = mfa_service
        self._session_lifetime = session_lifetime

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def authenticate(
        self,
        email: str,
        password: str,
        ip_address: str,
        user_agent: str,
    ) -> Result[AdminAuthResult, AdminAuthError]:
        """Authenticate an admin user through the full security pipeline.

        Steps executed in order:

        1. ``check_ip_rate_limit`` — raises ``RateLimitExceededError`` if the
           origin IP has exceeded the configured threshold.
        2. ``check_account_lockout`` — raises ``AccountLockedError`` if the
           account is temporarily or permanently locked.
        3. ``user_store.authenticate`` — returns ``None`` on invalid credentials.
        3b. Two-factor challenge — when the user has 2FA enabled, returns a
           result with ``mfa_required=True`` (no session created); the caller
           must finish via ``complete_mfa_login``.
        4. Record success attempt and clear lockout state.
        5. Create a new session via ``session_service``.
        6. Emit ``LOGIN_SUCCESS`` audit event.

        Args:
            email: Admin user email address.
            password: Plain-text password to verify.
            ip_address: Client IP address used for rate limiting and audit.
            user_agent: Client user-agent string used for audit.

        Returns:
            ``Ok(AdminAuthResult)`` containing session details on success.
            ``Ok(AdminAuthResult)`` with ``mfa_required=True`` (empty
            ``session_id``) when the user must complete a 2FA challenge.
            ``Err(RateLimitExceededError)`` when the IP is rate-limited.
            ``Err(AccountLockedError)`` when the account is locked.
            ``Err(InvalidCredentialsError)`` when credentials are invalid.
        """
        # Step 1 — IP rate limit
        try:
            await self._attempt_service.check_ip_rate_limit(ip_address)
        except RateLimitExceededError as exc:
            await self._attempt_service.record_attempt(
                email=email,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                failure_reason="ip_rate_limited",
            )
            await self._audit_service.log_event(
                event_type=AdminSecurityEventType.LOGIN_BLOCKED_IP,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                metadata={"email": email},
            )
            logger.warning(
                "admin_login_blocked_ip",
                ip_address=ip_address,
                email=email,
            )
            return Err(exc)

        # Step 2 — Account lockout
        try:
            await self._attempt_service.check_account_lockout(email)
        except AccountLockedError as exc:
            await self._audit_service.log_event(
                event_type=AdminSecurityEventType.LOGIN_BLOCKED_LOCKOUT,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                metadata={"email": email},
            )
            logger.warning(
                "admin_login_blocked_lockout",
                email=email,
                ip_address=ip_address,
            )
            return Err(exc)

        # Step 3 — Credential verification
        user: Any | None = await self._user_store.authenticate(email, password)
        if user is None:
            await self._attempt_service.record_attempt(
                email=email,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                failure_reason="invalid_credentials",
            )
            await self._audit_service.log_event(
                event_type=AdminSecurityEventType.LOGIN_FAILURE,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                metadata={"email": email},
            )
            logger.info(
                "admin_login_failure",
                email=email,
                ip_address=ip_address,
            )
            return Err(InvalidCredentialsError("Invalid email or password."))

        # Step 3b — Two-factor challenge (when enabled for this user)
        if self._mfa_service is not None:
            mfa_enabled = await self._mfa_service.is_enabled(str(user.user_id))
            if mfa_enabled:
                await self._audit_service.log_event(
                    event_type=AdminSecurityEventType.MFA_CHALLENGE_ISSUED,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=True,
                    admin_user_id=str(user.user_id),
                    metadata={"email": str(user.email)},
                )
                roles: list[str] = list(getattr(user, "roles", []) or [])
                return Ok(
                    AdminAuthResult(
                        session_id="",
                        user_id=str(user.user_id),
                        email=str(user.email),
                        roles=roles,
                        expires_at=datetime.now(UTC)
                        + timedelta(seconds=self._session_lifetime),
                        mfa_required=True,
                    )
                )

        # Step 4 — Record success and clear lockout
        await self._attempt_service.record_attempt(
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
            success=True,
        )
        await self._attempt_service.clear_lockout(email)

        # Step 5 — Create session
        roles: list[str] = list(getattr(user, "roles", []) or [])
        session_id: str = await self._session_service.create_session(
            user_id=str(user.user_id),
            email=str(user.email),
            roles=roles,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await self._audit_service.log_event(
            event_type=AdminSecurityEventType.SESSION_CREATED,
            ip_address=ip_address,
            user_agent=user_agent,
            success=True,
            admin_user_id=str(user.user_id),
            metadata={"email": str(user.email), "session_id": session_id},
        )

        expires_at: datetime = datetime.now(UTC) + timedelta(
            seconds=self._session_lifetime
        )

        # Step 6 — Audit success
        await self._audit_service.log_event(
            event_type=AdminSecurityEventType.LOGIN_SUCCESS,
            ip_address=ip_address,
            user_agent=user_agent,
            success=True,
            admin_user_id=str(user.user_id),
            metadata={"email": str(user.email), "session_id": session_id},
        )
        logger.info(
            "admin_login_success",
            user_id=str(user.user_id),
            email=str(user.email),
            ip_address=ip_address,
        )

        return Ok(
            AdminAuthResult(
                session_id=session_id,
                user_id=str(user.user_id),
                email=str(user.email),
                roles=roles,
                expires_at=expires_at,
            )
        )

    async def complete_mfa_login(
        self,
        user_id: str,
        email: str,
        roles: list[str],
        code: str,
        ip_address: str,
        user_agent: str,
    ) -> Result[AdminAuthResult, AdminAuthError]:
        """Complete a login after a successful TOTP challenge.

        Called by the 2FA form once the user supplies a valid code.  Runs
        the post-credential pipeline that ``authenticate`` deferred when it
        returned ``mfa_required=True``: attempt recording, lockout
        clearance, session creation, and audit logging.

        Args:
            user_id: Admin user UUID (from the pending challenge).
            email: Admin user email (from the pending challenge).
            roles: Role names for the user (from the pending challenge).
            code: TOTP code to verify.
            ip_address: Client IP address used for rate limiting and audit.
            user_agent: Client user-agent string used for audit.

        Returns:
            ``Ok(AdminAuthResult)`` with a real session on success.
            ``Err(MfaVerificationFailedError)`` when the code is invalid.
            ``Err(MfaNotEnabledError)`` when 2FA is unavailable.
        """
        if self._mfa_service is None:
            return Err(
                MfaNotEnabledError(
                    "Two-factor authentication is not enabled for this account."
                )
            )

        # Step 1 — Verify the TOTP code
        verification = await self._mfa_service.verify_code(user_id, code)
        if verification.is_err():
            await self._audit_service.log_event(
                event_type=AdminSecurityEventType.MFA_CHALLENGE_FAILED,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                admin_user_id=user_id,
                metadata={"email": email},
            )
            logger.warning("admin_mfa_code_not_available", user_id=user_id)
            return verification

        if not verification.unwrap():
            await self._audit_service.log_event(
                event_type=AdminSecurityEventType.MFA_CHALLENGE_FAILED,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                admin_user_id=user_id,
                metadata={"email": email},
            )
            await self._attempt_service.record_attempt(
                email=email,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                failure_reason="invalid_mfa_code",
            )
            logger.warning("admin_mfa_code_failed", user_id=user_id, email=email)
            return Err(MfaVerificationFailedError("Invalid verification code."))

        await self._audit_service.log_event(
            event_type=AdminSecurityEventType.MFA_VERIFIED,
            ip_address=ip_address,
            user_agent=user_agent,
            success=True,
            admin_user_id=user_id,
            metadata={"email": email},
        )

        # Step 2 — Record success and clear lockout
        await self._attempt_service.record_attempt(
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
            success=True,
        )
        await self._attempt_service.clear_lockout(email)

        # Step 3 — Create session
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

        # Step 4 — Audit success
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

        return Ok(
            AdminAuthResult(
                session_id=session_id,
                user_id=user_id,
                email=email,
                roles=roles,
                expires_at=expires_at,
            )
        )

    async def invalidate_session(self, session_id: str) -> None:
        """Revoke a single session (logout).

        Revokes the session via ``session_service`` and emits a ``LOGOUT``
        audit event. Audit failure is absorbed and never propagated.

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
        Audit failure is absorbed and never propagated.

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


__all__ = ["AdminAuthService"]
