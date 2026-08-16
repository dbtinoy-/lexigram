"""Tests for HMACSignatureVerifier."""

from __future__ import annotations
from enum import Enum

import hashlib
import hmac

import pytest

from lexigram.webhook.verification.hmac import HMACSignatureVerifier


class TestHMACSignatureVerifier:
    """Tests for HMACSignatureVerifier."""

    @pytest.fixture
    def verifier(self) -> HMACSignatureVerifier:
        """HMACSignatureVerifier instance."""
        return HMACSignatureVerifier()

    def test_compute_signature_format(self, verifier: HMACSignatureVerifier) -> None:
        """Signature includes sha256= prefix."""
        sig = verifier.compute_signature(b"hello", "secret")
        assert sig.startswith("sha256=")
        assert len(sig) == len("sha256=") + 64  # 32 bytes = 64 hex chars

    def test_compute_signature_matches_stdlib(
        self, verifier: HMACSignatureVerifier
    ) -> None:
        """Signature matches stdlib hmac.new result."""
        payload = b"test payload"
        secret = "mysecret"
        expected = (
            "sha256="
            + hmac.new(
                secret.encode("utf-8"), payload, hashlib.sha256
            ).hexdigest()
        )
        assert verifier.compute_signature(payload, secret) == expected

    def test_verify_prefixed_signature(self, verifier: HMACSignatureVerifier) -> None:
        """verify() accepts prefixed 'sha256=...' signature."""
        payload = b"data"
        secret = "key"
        sig = verifier.compute_signature(payload, secret)
        assert verifier.verify(payload, sig, secret) is True

    def test_verify_bare_signature(self, verifier: HMACSignatureVerifier) -> None:
        """verify() accepts bare signature without sha256= prefix."""
        payload = b"data"
        secret = "key"
        sig = verifier.compute_signature(payload, secret).removeprefix("sha256=")
        assert verifier.verify(payload, sig, secret) is True

    def test_verify_wrong_secret(self, verifier: HMACSignatureVerifier) -> None:
        """verify() returns False for wrong secret."""
        payload = b"data"
        sig = verifier.compute_signature(payload, "correct_secret")
        assert verifier.verify(payload, sig, "wrong_secret") is False

    def test_verify_tampered_payload(self, verifier: HMACSignatureVerifier) -> None:
        """verify() returns False for tampered payload."""
        secret = "key"
        sig = verifier.compute_signature(b"original", secret)
        assert verifier.verify(b"tampered", sig, secret) is False

    def test_verify_empty_payload(self, verifier: HMACSignatureVerifier) -> None:
        """verify() handles empty payload."""
        secret = "key"
        sig = verifier.compute_signature(b"", secret)
        assert verifier.verify(b"", sig, secret) is True
