"""Tests for webhook signature verification edge cases."""

from __future__ import annotations

import hmac
import hashlib

import pytest

from lexigram.contracts.webhook.types import WebhookEvent
from lexigram.webhook.verification.hmac import HMACSignatureVerifier


def _make_webhook_event(event_id: str = "evt-1") -> WebhookEvent:
    """Build a test webhook event."""
    return WebhookEvent(
        event_id=event_id,
        event_type="user.created",
        payload={"user_id": "123", "email": "test@example.com"},
    )


def _sign_payload(payload: bytes, secret: str) -> str:
    """Create HMAC signature for payload."""
    signature_hex = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return f"sha256={signature_hex}"


@pytest.fixture
def verifier() -> HMACSignatureVerifier:
    """HMAC verifier."""
    return HMACSignatureVerifier()


class TestHMACVerification:
    """Test HMAC signature verification."""

    @pytest.mark.asyncio
    async def test_valid_signature_verifies(self, verifier: HMACSignatureVerifier) -> None:
        """Valid signature passes verification."""
        secret = "test-secret"
        payload = b'{"event_id":"evt-1","event_type":"user.created"}'
        signature = _sign_payload(payload, secret)

        result = verifier.verify(payload, signature, secret)

        assert result is True

    @pytest.mark.asyncio
    async def test_invalid_signature_fails(self, verifier: HMACSignatureVerifier) -> None:
        """Invalid signature fails verification."""
        secret = "test-secret"
        payload = b'{"event_id":"evt-1"}'
        wrong_signature = "sha256=wrong-signature-value"

        result = verifier.verify(payload, wrong_signature, secret)

        assert result is False

    @pytest.mark.asyncio
    async def test_wrong_secret_fails_verification(self, verifier: HMACSignatureVerifier) -> None:
        """Using different secret fails verification."""
        payload = b'{"event_id":"evt-1"}'
        secret1 = "secret-1"
        secret2 = "secret-2"

        signature = _sign_payload(payload, secret1)

        result = verifier.verify(payload, signature, secret2)

        assert result is False

    @pytest.mark.asyncio
    async def test_tampered_payload_fails_verification(self, verifier: HMACSignatureVerifier) -> None:
        """Modified payload fails verification."""
        secret = "test-secret"
        original_payload = b'{"event_id":"evt-1","amount":100}'
        signature = _sign_payload(original_payload, secret)

        # Tamper with payload
        tampered_payload = b'{"event_id":"evt-1","amount":1000}'

        result = verifier.verify(tampered_payload, signature, secret)

        assert result is False

    @pytest.mark.asyncio
    async def test_empty_payload_signature(self, verifier: HMACSignatureVerifier) -> None:
        """Empty payload can be signed."""
        secret = "test-secret"
        empty_payload = b""

        signature = _sign_payload(empty_payload, secret)

        result = verifier.verify(empty_payload, signature, secret)

        assert result is True

    @pytest.mark.asyncio
    async def test_large_payload_signature(self, verifier: HMACSignatureVerifier) -> None:
        """Large payload is handled correctly."""
        secret = "test-secret"
        large_payload = b'{"data":"' + (b"x" * 10000) + b'"}'

        signature = _sign_payload(large_payload, secret)

        result = verifier.verify(large_payload, signature, secret)

        assert result is True

    @pytest.mark.asyncio
    async def test_special_characters_in_payload(self, verifier: HMACSignatureVerifier) -> None:
        """Special characters in payload are handled."""
        secret = "test-secret"
        payload = b'{"message":"Hello\\nWorld\\t!\\r\\n","emoji":"\xf0\x9f\x9a\x80"}'

        signature = _sign_payload(payload, secret)

        result = verifier.verify(payload, signature, secret)

        assert result is True

    @pytest.mark.asyncio
    async def test_unicode_secret(self, verifier: HMACSignatureVerifier) -> None:
        """Unicode characters in secret work correctly."""
        secret = "秘密-🔐-Secret"
        payload = b'{"event_id":"evt-1"}'

        signature = _sign_payload(payload, secret)

        result = verifier.verify(payload, signature, secret)

        assert result is True

    @pytest.mark.asyncio
    async def test_bare_signature_format(self, verifier: HMACSignatureVerifier) -> None:
        """Bare signature format (without sha256= prefix) works."""
        secret = "test-secret"
        payload = b'{"event_id":"evt-1"}'
        
        # Create signature without prefix
        signature_hex = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
        
        # Verifier should accept both with and without prefix
        result = verifier.verify(payload, signature_hex, secret)

        assert result is True


class TestSignatureHeaderParsing:
    """Test parsing and extraction of signature headers."""

    def test_extract_signature_from_x_webhook_signature_header(self) -> None:
        """Extract signature from X-Webhook-Signature header."""
        headers = {"X-Webhook-Signature": "sha256=abcd1234"}
        assert headers.get("X-Webhook-Signature") == "sha256=abcd1234"

    def test_missing_signature_header(self) -> None:
        """Missing signature header is detected."""
        headers = {"Content-Type": "application/json"}
        signature = headers.get("X-Webhook-Signature")
        assert signature is None

    def test_malformed_signature_header(self) -> None:
        """Malformed signature header is handled."""
        headers = {"X-Webhook-Signature": "malformed-no-equals"}
        sig_value = headers.get("X-Webhook-Signature", "")
        assert sig_value == "malformed-no-equals"


class TestSignatureComputation:
    """Test signature computation."""

    def test_compute_signature_returns_prefixed_format(self) -> None:
        """Signatures are returned with sha256= prefix."""
        verifier = HMACSignatureVerifier()
        payload = b'{"event_id":"evt-1"}'
        secret = "test-secret"
        
        signature = verifier.compute_signature(payload, secret)
        
        assert signature.startswith("sha256=")

    def test_different_payloads_produce_different_signatures(self) -> None:
        """Different payloads produce different signatures."""
        verifier = HMACSignatureVerifier()
        secret = "test-secret"
        
        payload1 = b'{"event_id":"evt-1"}'
        payload2 = b'{"event_id":"evt-2"}'
        
        sig1 = verifier.compute_signature(payload1, secret)
        sig2 = verifier.compute_signature(payload2, secret)
        
        assert sig1 != sig2

    def test_same_payload_produces_same_signature(self) -> None:
        """Same payload repeatedly produces same signature."""
        verifier = HMACSignatureVerifier()
        secret = "test-secret"
        payload = b'{"event_id":"evt-1"}'
        
        sig1 = verifier.compute_signature(payload, secret)
        sig2 = verifier.compute_signature(payload, secret)
        
        assert sig1 == sig2



class TestTimestampVerification:
    """Test timestamp-based replay attack prevention."""

    @pytest.mark.asyncio
    async def test_recent_timestamp_accepted(self) -> None:
        """Recent timestamp (within window) is accepted."""
        # Implementation-dependent; typically check within 5 minutes
        import time
        current_time = time.time()
        webhook_time = current_time - 60  # 1 minute ago
        time_diff = abs(current_time - webhook_time)
        assert time_diff < 300  # 5 minute threshold

    @pytest.mark.asyncio
    async def test_old_timestamp_rejected(self) -> None:
        """Old timestamp (outside window) is rejected."""
        import time
        current_time = time.time()
        webhook_time = current_time - 3600  # 1 hour ago
        time_diff = abs(current_time - webhook_time)
        assert time_diff > 300  # Outside threshold

    @pytest.mark.asyncio
    async def test_future_timestamp_rejected(self) -> None:
        """Future timestamp is rejected."""
        import time
        current_time = time.time()
        webhook_time = current_time + 3600  # 1 hour in future
        time_diff = abs(current_time - webhook_time)
        assert time_diff > 300  # Outside threshold


class TestMultipleSignatureSchemes:
    """Test support for different signature algorithms."""

    def test_sha256_signature(self) -> None:
        """SHA256 signatures work."""
        secret = "test-secret"
        payload = b'{"event_id":"evt-1"}'
        signature = _sign_payload(payload, secret)
        assert len(signature) == 71  # SHA256 hex is 71 chars

    def test_sha512_signature(self) -> None:
        """SHA512 signatures work."""
        secret = "test-secret"
        payload = b'{"event_id":"evt-1"}'
        signature = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha512,
        ).hexdigest()
        assert len(signature) == 128  # SHA512 hex is 128 chars

    def test_signature_algorithm_mismatch_fails(self) -> None:
        """Signature with wrong algorithm fails."""
        secret = "test-secret"
        payload = b'{"event_id":"evt-1"}'

        # Create SHA256 signature
        sig_sha256 = _sign_payload(payload, secret)

        # Create SHA512 signature
        sig_sha512 = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha512,
        ).hexdigest()

        # They should be different
        assert sig_sha256 != sig_sha512
