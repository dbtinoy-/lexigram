"""TOTP two-factor authentication service for the admin panel.

Owns the 2FA lifecycle: secret generation, QR provisioning, code
verification, and disable.  Depends only on the MFA store protocol and
(optionally) the audit log service, so it is trivially testable without
a database.
"""

from __future__ import annotations

import pyotp
import segno

from lexigram.admin.auth.errors import (
    AdminAuthError,
    MfaNotEnabledError,
    MfaVerificationFailedError,
)
from lexigram.admin.auth.protocols import (
    AdminAuditLogServiceProtocol,
    AdminMfaStoreProtocol,
)
from lexigram.admin.auth.types import AdminSecurityEventType
from lexigram.admin.config import AdminMfaConfig
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result

logger = get_logger(__name__)


class AdminMfaService:
    """TOTP 2FA lifecycle: setup, verify, disable.

    Args:
        config: MFA configuration (issuer, skew, enabled flag).
        store: Persistence for per-user TOTP secrets.
        audit_service: Optional security-event recorder; ``None`` skips
            audit logging (e.g. in tests).
    """

    def __init__(
        self,
        config: AdminMfaConfig,
        store: AdminMfaStoreProtocol,
        audit_service: AdminAuditLogServiceProtocol | None = None,
    ) -> None:
        self._config = config
        self._store = store
        self._audit_service = audit_service

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def is_enabled(self, user_id: str) -> bool:
        """Return True when 2FA is enabled for the user."""
        return await self._store.is_enabled(user_id)

    async def start_setup(
        self, user_id: str, email: str
    ) -> Result[tuple[str, str, str], AdminAuthError]:
        """Generate a new TOTP secret, provisioning URI, and QR SVG.

        Nothing is persisted here — the secret travels via the caller
        (session) and is committed by ``confirm_setup``.

        Args:
            user_id: Admin user UUID.
            email: Admin user email (embedded in the provisioning URI).

        Returns:
            ``Ok((secret, otpauth_uri, svg))`` on success.
            ``Err(MfaNotEnabledError)`` when 2FA is disabled in config.
        """
        if not self._config.enabled:
            return Err(
                MfaNotEnabledError(
                    "Two-factor authentication is disabled for this panel."
                )
            )
        secret = pyotp.random_base32()
        uri = pyotp.TOTP(secret).provisioning_uri(
            name=email, issuer_name=self._config.issuer
        )
        svg = segno.make(uri).svg_inline(scale=4)
        return Ok((secret, uri, svg))

    async def confirm_setup(
        self, user_id: str, secret: str, code: str
    ) -> Result[None, AdminAuthError]:
        """Validate a code against a new secret and persist it.

        Args:
            user_id: Admin user UUID.
            secret: TOTP secret (from ``start_setup``).
            code: TOTP code to validate.

        Returns:
            ``Ok(None)`` when the code is valid and the secret is stored.
            ``Err(MfaVerificationFailedError)`` when the code is invalid.
            ``Err(MfaNotEnabledError)`` when 2FA is disabled in config.
        """
        if not self._config.enabled:
            return Err(
                MfaNotEnabledError(
                    "Two-factor authentication is disabled for this panel."
                )
            )
        if not pyotp.TOTP(secret).verify(code, valid_window=self._config.skew):
            return Err(MfaVerificationFailedError("Invalid verification code."))
        await self._store.save_secret(user_id, secret)
        if self._audit_service is not None:
            await self._audit_service.log_event(
                event_type=AdminSecurityEventType.MFA_ENABLED,
                ip_address="",
                user_agent="",
                success=True,
                admin_user_id=user_id,
                metadata={},
            )
        logger.info("admin_mfa_enabled", user_id=user_id)
        return Ok(None)

    async def verify_code(
        self, user_id: str, code: str
    ) -> Result[bool, AdminAuthError]:
        """Validate a TOTP code for a user without persisting anything.

        Args:
            user_id: Admin user UUID.
            code: TOTP code to validate.

        Returns:
            ``Ok(True)`` for a valid code, ``Ok(False)`` otherwise.
            ``Err(MfaNotEnabledError)`` when the user has no stored secret.
        """
        secret = await self._store.get_secret(user_id)
        if secret is None:
            return Err(
                MfaNotEnabledError(
                    "Two-factor authentication is not enabled for this account."
                )
            )
        return Ok(pyotp.TOTP(secret).verify(code, valid_window=self._config.skew))

    async def disable(
        self, user_id: str, code: str
    ) -> Result[bool, AdminAuthError]:
        """Disable 2FA for a user (requires a valid current code).

        Args:
            user_id: Admin user UUID.
            code: Current TOTP code proving possession of the secret.

        Returns:
            ``Ok(True)`` when disabled.
            ``Err(MfaNotEnabledError)`` when 2FA is not enabled.
            ``Err(MfaVerificationFailedError)`` when the code is invalid.
        """
        result = await self.verify_code(user_id, code)
        if result.is_err():
            return result
        if not result.unwrap():
            return Err(MfaVerificationFailedError("Invalid verification code."))
        await self._store.disable(user_id)
        if self._audit_service is not None:
            await self._audit_service.log_event(
                event_type=AdminSecurityEventType.MFA_DISABLED,
                ip_address="",
                user_agent="",
                success=True,
                admin_user_id=user_id,
                metadata={},
            )
        logger.info("admin_mfa_disabled", user_id=user_id)
        return Ok(True)


__all__ = ["AdminMfaService"]
