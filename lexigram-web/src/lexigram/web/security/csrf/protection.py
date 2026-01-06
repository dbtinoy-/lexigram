"""CSRF token generation and validation.

Provides :class:`CSRFProtection`, which implements the double-submit cookie
pattern: generates HMAC-bound tokens and validates them on incoming requests.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

from lexigram.web.security.config import CSRFConfig


class CSRFProtection:
    """CSRF protection implementation using double-submit cookie pattern.

    This implementation follows OWASP guidelines for CSRF protection:

    * Generates a cryptographically secure random token.
    * Stores token in a cookie (accessible via JavaScript).
    * Requires the same token in a request header for state-changing operations.
    * Uses HMAC for token validation to prevent tampering.

    Example::

        config = CSRFConfig(cookie_name="csrf", header_name="X-CSRF-Token")
        csrf = CSRFProtection(config)

        token = csrf.generate_token(session_id="user-123")
        is_valid = csrf.validate_token(token, session_id="user-123")
    """

    def __init__(self, config: CSRFConfig | None = None) -> None:
        """Initialize CSRF protection with configuration.

        Args:
            config: CSRF configuration. Uses defaults if not provided.
        """
        self._config = config or CSRFConfig()

    def generate_token(self, session_id: str) -> str:
        """Generate a CSRF token for the given session.

        Args:
            session_id: The user's session identifier.

        Returns:
            A cryptographically secure CSRF token.

        Raises:
            ValueError: If ``config.secret_key`` is ``None``, since token
                generation requires an HMAC secret.
        """
        if self._config.secret_key is None:
            raise ValueError(
                "CSRFConfig.secret_key must be set to generate CSRF tokens"
            )
        random_part = secrets.token_bytes(self._config.token_length)
        hmac_part = hmac.new(
            self._config.secret_key.encode(),
            f"{session_id}".encode(),
            hashlib.sha256,
        ).digest()
        token = random_part + hmac_part
        return token.hex()

    def validate_token(self, token: str, session_id: str) -> bool:
        """Validate a CSRF token for the given session.

        Args:
            token: The token to validate.
            session_id: The expected session identifier.

        Returns:
            True if the token is valid for the session, False otherwise.

        Raises:
            ValueError: If ``config.secret_key`` is ``None``, since token
                validation requires an HMAC secret.
        """
        if self._config.secret_key is None:
            raise ValueError(
                "CSRFConfig.secret_key must be set to validate CSRF tokens"
            )
        if not token or not session_id:
            return False

        try:
            expected_length = self._config.token_length * 2 + 64
            if len(token) != expected_length:
                return False

            provided_hmac_hex = token[self._config.token_length * 2 :]

            expected_hmac = hmac.new(
                self._config.secret_key.encode(),
                f"{session_id}".encode(),
                hashlib.sha256,
            ).hexdigest()

            return hmac.compare_digest(provided_hmac_hex, expected_hmac)
        except (ValueError, TypeError):
            return False

    @property
    def config(self) -> CSRFConfig:
        """Get the CSRF configuration."""
        return self._config


__all__ = ["CSRFProtection"]
