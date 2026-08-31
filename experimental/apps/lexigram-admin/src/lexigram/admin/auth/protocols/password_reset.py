"""Persistence and orchestration protocols for password reset."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from datetime import datetime

    from lexigram.admin.auth.errors import AdminAuthError
    from lexigram.admin.auth.types import AdminPasswordResetToken
    from lexigram.result import Result


@runtime_checkable
class AdminPasswordResetTokenStoreProtocol(Protocol):
    """Persistence contract for password reset tokens.

    Implementations:
        - :class:`~lexigram.admin.auth.store.password_reset_token_sql.AdminPasswordResetTokenSqlStore`
    """

    async def ensure_schema(self) -> None:
        """Create the token table if it does not exist."""
        ...

    async def create(self, email: str, token_hash: str, expires_at: datetime) -> None:
        """Persist a new token record.

        Args:
            email: Email the token is issued for.
            token_hash: sha256 hex digest of the raw token.
            expires_at: UTC expiry timestamp.
        """
        ...

    async def find_by_hash(self, token_hash: str) -> AdminPasswordResetToken | None:
        """Look up a token by its sha256 hash.

        Args:
            token_hash: sha256 hex digest of the raw token.

        Returns:
            Token record or ``None`` when unknown.
        """
        ...

    async def mark_consumed(self, token_hash: str) -> bool:
        """Atomically verify-and-consume a token in one statement.

        Args:
            token_hash: sha256 hex digest of the raw token.

        Returns:
            ``True`` only when the token existed, was unconsumed, and had
            not expired at the instant of the write; ``False`` otherwise
            — the caller cannot distinguish missing, already-consumed,
            or expired without a separate lookup.
        """
        ...


@runtime_checkable
class AdminPasswordResetServiceProtocol(Protocol):
    """Password reset orchestration contract."""

    async def request_reset(
        self,
        email: str,
        ip_address: str,
        user_agent: str,
        base_url: str,
        admin_prefix: str = "/admin",
    ) -> Result[None, AdminAuthError]:
        """Issue a reset token and notify the user.

        Always returns ``Ok(None)`` for unknown emails (anti-enumeration).
        """
        ...

    async def confirm_reset(
        self,
        token: str,
        new_password: str,
        ip_address: str = "",
        user_agent: str = "",
    ) -> Result[None, AdminAuthError]:
        """Validate a token and apply a new password.

        Consumes the token on success and invalidates all user sessions.
        """
        ...
