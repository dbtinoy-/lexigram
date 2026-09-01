"""Email verification persistence and service protocols."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from datetime import datetime

    from lexigram.admin.auth.errors import AdminAuthError
    from lexigram.result import Result


@runtime_checkable
class AdminEmailVerificationStoreProtocol(Protocol):
    """Persistence contract for admin email verification state.

    Implementations:
        - :class:`~lexigram.admin.auth.store.email_verification_sql.AdminEmailVerificationSqlStore`
    """

    async def ensure_schema(self) -> None:
        """Create the verification table if it does not exist."""
        ...

    async def is_verified(self, user_id: str) -> bool:
        """Return True when the user's email is verified.

        Args:
            user_id: Admin user UUID.
        """
        ...

    async def find_user_by_token_hash(self, token_hash: str) -> str | None:
        """Look up the user owning an unconsumed token.

        Args:
            token_hash: sha256 hex digest of the raw token.

        Returns:
            User UUID or ``None`` when no unconsumed token matches.
        """
        ...

    async def save_token(
        self, user_id: str, token_hash: str, expires_at: datetime
    ) -> None:
        """Persist (or refresh) the verification token for a user.

        Args:
            user_id: Admin user UUID.
            token_hash: sha256 hex digest of the raw token.
            expires_at: UTC expiry timestamp.
        """
        ...

    async def consume_token(self, user_id: str, token_hash: str) -> bool:
        """Atomically verify + consume a token.

        Marks the email verified and clears the token when the hash matches,
        the token is unexpired, and the email is not already verified.

        Args:
            user_id: Admin user UUID.
            token_hash: sha256 hex digest of the raw token.

        Returns:
            ``True`` when the token was valid and consumed.
        """
        ...

    async def mark_verified(self, user_id: str) -> None:
        """Mark a user's email verified without a token round-trip.

        Used for accounts whose email ownership is proven out-of-band —
        e.g. the first admin created through the setup wizard, who already
        presented the deployment's setup token.

        Args:
            user_id: Admin user UUID.
        """
        ...

    async def clear_token(self, user_id: str) -> None:
        """Remove the pending verification token for a user.

        Args:
            user_id: Admin user UUID.
        """
        ...


@runtime_checkable
class AdminEmailVerificationServiceProtocol(Protocol):
    """Email verification orchestration contract.

    Implementations:
        - :class:`~lexigram.admin.auth.services.email_verification_service.AdminEmailVerificationService`
    """

    async def is_verified(self, user_id: str) -> bool:
        """Return True when the user's email is verified."""
        ...

    async def is_required(self, user_id: str) -> bool:
        """Return True when login must be gated on email verification."""
        ...

    async def send_verification(
        self,
        user_id: str,
        email: str,
        user_name: str,
        base_url: str = "",
        ip_address: str = "",
        admin_prefix: str = "/admin",
    ) -> Result[None, AdminAuthError]:
        """Issue a verification link and email it to the user.

        No-op (Ok) when disabled or already verified; fail-open on delivery.
        Rate limited per IP when a cache backend is wired (fail open).
        """
        ...

    async def verify_token(self, token: str) -> Result[bool, AdminAuthError]:
        """Validate and consume a verification token.

        Returns:
            ``Ok(True)`` on success; ``Err(EmailVerificationTokenInvalidError)``
            for unknown/used/expired tokens.
        """
        ...

    async def mark_verified(self, user_id: str) -> None:
        """Mark a user's email verified without sending a verification link.

        Used when ownership is proven out-of-band (e.g. the setup wizard's
        first admin, authenticated by the deployment setup token).

        Args:
            user_id: Admin user UUID.
        """
        ...

    async def resend_verification(
        self,
        user_id: str,
        email: str,
        user_name: str,
        base_url: str = "",
        ip_address: str = "",
        admin_prefix: str = "/admin",
    ) -> Result[None, AdminAuthError]:
        """Re-issue and re-send the verification email."""
        ...
