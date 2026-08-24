"""Admin authentication orchestration service protocol."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from lexigram.admin.auth.errors import AdminAuthError
    from lexigram.admin.auth.types import AdminAuthResult
    from lexigram.result import Result


@runtime_checkable
class AdminAuthServiceProtocol(Protocol):
    """Main authentication orchestration service protocol.

    Coordinates credential verification, rate limiting, lockout checks,
    session issuance, and audit logging.
    """

    async def authenticate(
        self,
        email: str,
        password: str,
        ip_address: str,
        user_agent: str,
    ) -> Result[AdminAuthResult, AdminAuthError]:
        """Authenticate an admin user with full security pipeline.

        Args:
            email: Admin user email.
            password: Plain-text password.
            ip_address: Client IP for rate limiting.
            user_agent: Client user agent for audit.

        Returns:
            Ok(AdminAuthResult) with session details on success.
            Err with specific AdminAuthError subclass on failure.
        """
        ...

    async def invalidate_session(self, session_id: str) -> None:
        """Invalidate a session (logout).

        Args:
            session_id: Session identifier to revoke.
        """
        ...

    async def invalidate_all_user_sessions(self, user_id: str) -> None:
        """Revoke all active sessions for a user (e.g., after password change).

        Args:
            user_id: Admin user UUID whose sessions to revoke.
        """
        ...

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

        Verifies the code, then runs the post-credential pipeline
        (attempt recording, lockout clearance, session creation, audits)
        that was deferred when ``authenticate`` returned ``mfa_required``.

        Args:
            user_id: Admin user UUID (from the pending challenge).
            email: Admin user email (from the pending challenge).
            roles: Role names for the user (from the pending challenge).
            code: TOTP code to verify.
            ip_address: Client IP for rate limiting.
            user_agent: Client user agent for audit.

        Returns:
            Ok(AdminAuthResult) with a real session on success.
            Err(MfaVerificationFailedError) when the code is invalid.
            Err(MfaNotEnabledError) when 2FA is unavailable.
        """
        ...
