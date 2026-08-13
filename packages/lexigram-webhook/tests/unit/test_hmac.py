"""Tests for HMAC signature verification."""

from __future__ import annotations

import pytest

from lexigram.webhook.verification.hmac import HMACSignatureVerifier


class TestHMACSignatureVerifier:
    """Tests for HMACSignatureVerifier."""

    @pytest.fixture
    def verifier(self) -> HMACSignatureVerifier:
        """Create verifier instance."""
        return HMACSignatureVerifier()

    def test_compute_signature_format(self, verifier: HMACSignatureVerifier) -> None:
        """Verify signature has correct prefix."""
        payload = b'{"event": "test"}'
        secret = "test_secret"
        sig = verifier.compute_signature(payload, secret)
        assert sig.startswith("sha256=")
        assert len(sig) == 7 + 64

    def test_compute_signature_deterministic(
        self, verifier: HMACSignatureVerifier
    ) -> None:
        """Same payload produces same signature."""
        payload = b'{"event": "test"}'
        secret = "test_secret"
        sig1 = verifier.compute_signature(payload, secret)
        sig2 = verifier.compute_signature(payload, secret)
        assert sig1 == sig2

    def test_compute_signature_different_secret(
        self, verifier: HMACSignatureVerifier
    ) -> None:
        """Different secrets produce different signatures."""
        payload = b'{"event": "test"}'
        sig1 = verifier.compute_signature(payload, "secret1")
        sig2 = verifier.compute_signature(payload, "secret2")
        assert sig1 != sig2

    def test_compute_signature_different_payload(
        self, verifier: HMACSignatureVerifier
    ) -> None:
        """Different payloads produce different signatures."""
        secret = "test_secret"
        sig1 = verifier.compute_signature(b'{"event": "a"}', secret)
        sig2 = verifier.compute_signature(b'{"event": "b"}', secret)
        assert sig1 != sig2

    def test_verify_valid_signature(self, verifier: HMACSignatureVerifier) -> None:
        """Valid signature verifies successfully."""
        payload = b'{"event": "test"}'
        secret = "test_secret"
        signature = verifier.compute_signature(payload, secret)
        assert verifier.verify(payload, signature, secret) is True

    def test_verify_with_prefix(self, verifier: HMACSignatureVerifier) -> None:
        """Signature with sha256= prefix works."""
        payload = b'{"event": "test"}'
        secret = "test_secret"
        signature = f"sha256={verifier.compute_signature(payload, secret).removeprefix('sha256=')}"
        assert verifier.verify(payload, signature, secret) is True

    def test_verify_invalid_signature(self, verifier: HMACSignatureVerifier) -> None:
        """Invalid signature returns False."""
        payload = b'{"event": "test"}'
        secret = "test_secret"
        assert verifier.verify(payload, "sha256=invalidsig", secret) is False

    def test_verify_wrong_secret(self, verifier: HMACSignatureVerifier) -> None:
        """Wrong secret returns False."""
        payload = b'{"event": "test"}'
        signature = verifier.compute_signature(payload, "correct_secret")
        assert verifier.verify(payload, signature, "wrong_secret") is False

    def test_verify_empty_payload(self, verifier: HMACSignatureVerifier) -> None:
        """Empty payload verifies with correct signature."""
        payload = b""
        secret = "test_secret"
        signature = verifier.compute_signature(payload, secret)
        assert verifier.verify(payload, signature, secret) is True