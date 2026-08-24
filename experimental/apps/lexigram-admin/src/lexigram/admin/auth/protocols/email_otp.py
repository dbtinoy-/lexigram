"""Email one-time-password persistence and service protocols."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from datetime import datetime

    from lexigram.admin.auth.errors import AdminAuthError
    from lexigram.result import Result


@runtime_checkable
class AdminEmailOtpStoreProtocol(Protocol):
    """Persistence contract for email one-time-password codes.

    Implementations:
        - :class:`~lexigram.admin.auth.store.email_otp_sql.AdminEmailOtpSqlStore`
    """

    async def ensure_schema(self) -> None:
        """Create the OTP table if it does not exist."""
        ...

    async def save(self, user_id: str, code_hash: str, expires_at: datetime) -> None:
        """Persist a new emailed code.

        Args:
            user_id: Admin user UUID.
            code_hash: sha256 hex digest of the raw code.
            expires_at: UTC expiry timestamp.
        """
        ...

    async def consume(self, user_id: str, code_hash: str) -> bool:
        """Atomically consume a matching unexpired code.

        Args:
            user_id: Admin user UUID.
            code_hash: sha256 hex digest of the raw code.

        Returns:
            ``True`` when an unexpired, unused code matched and was consumed.
        """
        ...

    async def last_sent_at(self, user_id: str) -> datetime | None:
        """Return the creation time of the most recent code.

        Args:
            user_id: Admin user UUID.

        Returns:
            UTC datetime of the newest code, or ``None`` when none exists.
        """
        ...


@runtime_checkable
class AdminEmailOtpServiceProtocol(Protocol):
    """Email one-time-password factor contract.

    Implementations:
        - :class:`~lexigram.admin.auth.services.email_otp_service.AdminEmailOtpService`
    """

    async def send_otp(
        self, user_id: str, email: str, user_name: str
    ) -> Result[None, AdminAuthError]:
        """Generate, persist, and email a fresh one-time code.

        Returns:
            ``Ok(None)`` on success; ``Err`` when disabled, in cooldown, or
            undeliverable.
        """
        ...

    async def verify_otp(self, user_id: str, code: str) -> Result[bool, AdminAuthError]:
        """Verify a code and consume it when valid.

        Returns:
            ``Ok(True)`` on match; ``Ok(False)`` otherwise;
            ``Err`` when the factor is disabled.
        """
        ...
