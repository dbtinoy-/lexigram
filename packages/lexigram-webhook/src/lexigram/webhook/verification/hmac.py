"""HMAC-SHA256 webhook signature verifier."""

from __future__ import annotations

import hashlib
import hmac as _hmac


class HMACSignatureVerifier:
    """HMAC-SHA256 webhook signature verifier.

    Uses constant-time comparison to prevent timing side-channel attacks.
    Signature format: ``"sha256=<hex_digest>"`` (Stripe/GitHub compatible).
    """

    def verify(self, payload: bytes, signature: str, secret: str) -> bool:
        """Verify that the signature matches the payload.

        Supports both prefixed (``"sha256=abc123"``) and bare (``"abc123"``) formats.

        Args:
            payload: Raw request body bytes.
            signature: Received signature header value.
            secret: Shared secret for this subscription.

        Returns:
            True if the signature is valid.
        """
        expected_bare = self.compute_signature(payload, secret).removeprefix("sha256=")
        actual_bare = signature.removeprefix("sha256=")
        return _hmac.compare_digest(actual_bare, expected_bare)

    def compute_signature(self, payload: bytes, secret: str) -> str:
        """Compute HMAC-SHA256 signature with sha256= prefix.

        Args:
            payload: Raw payload bytes to sign.
            secret: Shared secret string.

        Returns:
            Signature string in ``"sha256=<hex_digest>"`` format.
        """
        digest = _hmac.new(
            secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return f"sha256={digest}"


__all__ = ["HMACSignatureVerifier"]
