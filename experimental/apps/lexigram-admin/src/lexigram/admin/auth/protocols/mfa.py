"""TOTP multi-factor authentication protocols."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from lexigram.admin.auth.errors import AdminAuthError
    from lexigram.result import Result


@runtime_checkable
class AdminMfaStoreProtocol(Protocol):
    """Persistence contract for per-user TOTP secrets.

    Implementations:
        - :class:`~lexigram.admin.auth.store.mfa_sql.AdminMfaSqlStore`
    """

    async def ensure_schema(self) -> None:
        """Create the MFA table if it does not exist."""
        ...

    async def is_enabled(self, user_id: str) -> bool:
        """Return True when 2FA is enabled for the user."""
        ...

    async def get_secret(self, user_id: str) -> str | None:
        """Return the stored TOTP secret (None when disabled)."""
        ...

    async def save_secret(self, user_id: str, secret: str) -> None:
        """Persist (or refresh) the TOTP secret for a user."""
        ...

    async def disable(self, user_id: str) -> None:
        """Remove the TOTP secret (2FA off)."""
        ...


@runtime_checkable
class AdminMfaServiceProtocol(Protocol):
    """TOTP 2FA orchestration contract.

    Implementations:
        - :class:`~lexigram.admin.auth.services.mfa_service.AdminMfaService`
    """

    async def is_enabled(self, user_id: str) -> bool:
        """Return True when 2FA is enabled for the user."""
        ...

    async def start_setup(
        self, user_id: str, email: str
    ) -> Result[tuple[str, str, str], AdminAuthError]:
        """Generate a TOTP secret, provisioning URI, and QR SVG (no persist).

        Returns:
            ``Ok((secret, otpauth_uri, svg))`` on success; ``Err`` when 2FA
            is disabled in configuration.
        """
        ...

    async def confirm_setup(
        self, user_id: str, secret: str, code: str
    ) -> Result[None, AdminAuthError]:
        """Validate a code against a new secret and persist it."""
        ...

    async def verify_code(
        self, user_id: str, code: str
    ) -> Result[bool, AdminAuthError]:
        """Validate a TOTP code; ``Err`` when 2FA is not enabled."""
        ...

    async def disable(self, user_id: str, code: str) -> Result[bool, AdminAuthError]:
        """Disable 2FA (requires a valid current code)."""
        ...

    def get_factor(self) -> str:
        """Return the configured second factor (``"totp"`` or ``"email"``)."""
        ...
