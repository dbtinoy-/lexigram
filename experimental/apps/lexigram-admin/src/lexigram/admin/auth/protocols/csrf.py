"""CSRF token generation and validation protocol."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class AdminCsrfServiceProtocol(Protocol):
    """CSRF token generation and validation service."""

    def generate_token(self, session_id: str) -> str:
        """Generate a CSRF token scoped to the given session.

        Token format: base64url(timestamp:nonce:hmac_signature)

        Args:
            session_id: Session ID to scope the token to.

        Returns:
            CSRF token string.
        """
        ...

    def validate_token(self, session_id: str, token: str) -> bool:
        """Validate a CSRF token against the session.

        Uses hmac.compare_digest for timing-safe comparison.

        Args:
            session_id: Session ID the token was generated for.
            token: Token to validate.

        Returns:
            True if valid and not expired, False otherwise.
        """
        ...
