"""HMAC signer — signs and verifies webhook payloads."""

from __future__ import annotations

import hashlib
import hmac


class HmacSigner:
    """Signs and verifies webhook payloads using HMAC-SHA256.

    Demonstrates webhook signature patterns for secure payload verification.
    """

    def __init__(self, secret: str) -> None:
        self._secret = secret.encode()

    def sign(self, payload: bytes) -> str:
        """Generate HMAC signature for a payload."""
        signature = hmac.new(self._secret, payload, hashlib.sha256).hexdigest()
        return f"sha256={signature}"

    def verify(self, payload: bytes, signature: str) -> bool:
        """Verify HMAC signature for a payload."""
        expected = self.sign(payload)
        return hmac.compare_digest(expected, signature)

    def extract_signature(self, header: str) -> str | None:
        """Extract signature from header value."""
        if header.startswith("sha256="):
            return header
        return None
