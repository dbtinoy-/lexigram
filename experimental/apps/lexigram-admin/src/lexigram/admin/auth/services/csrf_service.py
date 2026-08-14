"""Admin CSRF token generation and validation service."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time

from lexigram.admin.auth.protocols import AdminCsrfServiceProtocol
from lexigram.di.decorators import inject
from lexigram.logging import get_logger

logger = get_logger(__name__)

# Token wire format (before base64url encoding):
#   "{timestamp}:{nonce}:{hmac_signature}"
#
# HMAC message:  f"{session_id}:{timestamp}:{nonce}"
# HMAC key:      sha256(secret.encode())   — derived once at construction time
# HMAC digest:   SHA-256 hexdigest


@inject
class AdminCsrfService:
    """CSRF token generation and validation service.

    Tokens are HMAC-SHA256 signed, scoped to a specific session ID,
    and expire after a configurable lifetime (default 1 hour).
    Validation uses ``hmac.compare_digest`` for timing-safe comparison.
    """

    def __init__(
        self,
        secret: str,
        token_lifetime: int = 3600,
    ) -> None:
        """Initialize with signing secret.

        Args:
            secret: HMAC signing secret (use AdminAuthConfig.session_secret).
            token_lifetime: Token validity in seconds (default 3600 = 1 hour).
        """
        # Derive a fixed-length key from the caller-supplied secret so that
        # the key is always exactly 32 bytes regardless of secret length.
        self._key: bytes = hashlib.sha256(secret.encode()).digest()
        self._lifetime: int = token_lifetime

    @property
    def token_lifetime_seconds(self) -> int:
        """Return the configured token lifetime in seconds."""
        return self._lifetime

    # ------------------------------------------------------------------
    # AdminCsrfServiceProtocol
    # ------------------------------------------------------------------

    def generate_token(self, session_id: str) -> str:
        """Generate a CSRF token scoped to the given session.

        Token format: ``base64url("{timestamp}:{nonce}:{hmac_signature}")``.

        Args:
            session_id: Session ID to scope this token to.

        Returns:
            URL-safe base64-encoded CSRF token string.
        """
        timestamp = str(int(time.time()))
        nonce = secrets.token_hex(16)
        message = f"{session_id}:{timestamp}:{nonce}"
        signature = hmac.new(self._key, message.encode(), hashlib.sha256).hexdigest()
        raw = f"{timestamp}:{nonce}:{signature}"
        token = base64.urlsafe_b64encode(raw.encode()).decode()
        logger.debug("csrf.token_generated", session_id=session_id)
        return token

    def validate_token(self, session_id: str, token: str) -> bool:
        """Validate a CSRF token against the session.

        Uses ``hmac.compare_digest`` for timing-safe comparison.

        Args:
            session_id: Session ID the token was generated for.
            token: Token to validate (base64url-encoded).

        Returns:
            True if the token is valid and not expired, False otherwise.
        """
        try:
            raw = base64.urlsafe_b64decode(token.encode()).decode()
            parts = raw.split(":", 2)
            if len(parts) != 3:
                logger.debug("csrf.token_malformed", session_id=session_id)
                return False

            timestamp_str, nonce, provided_signature = parts

            # Expiry check
            token_age = int(time.time()) - int(timestamp_str)
            if token_age > self._lifetime:
                logger.debug(
                    "csrf.token_expired",
                    session_id=session_id,
                    age_seconds=token_age,
                )
                return False

            # Recompute and compare in constant time
            message = f"{session_id}:{timestamp_str}:{nonce}"
            expected_signature = hmac.new(
                self._key, message.encode(), hashlib.sha256
            ).hexdigest()

            valid = hmac.compare_digest(expected_signature, provided_signature)
            if not valid:
                logger.debug("csrf.token_signature_mismatch", session_id=session_id)
            return valid

        except (ValueError, TypeError) as exc:
            logger.debug(
                "csrf.token_validation_error",
                session_id=session_id,
                error=str(exc),
            )
            return False


# Verify that the concrete class satisfies the protocol at import time.
_: AdminCsrfServiceProtocol = AdminCsrfService.__new__(AdminCsrfService)

__all__ = ["AdminCsrfService"]
