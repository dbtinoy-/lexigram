"""Tests for verification helpers module."""

from __future__ import annotations

import pytest

from lexigram.webhook.verification.helpers import (
    WebhookHeaders,
    extract_webhook_headers,
    verify_webhook_payload,
)


class TestWebhookHeaders:
    """Tests for WebhookHeaders dataclass."""

    def test_create_with_all_values(self) -> None:
        """WebhookHeaders can be created with all values."""
        headers = WebhookHeaders(
            event_id="evt-123",
            event_type="user.created",
            signature="abc123",
            timestamp="2024-01-01T00:00:00Z",
        )
        assert headers.event_id == "evt-123"
        assert headers.event_type == "user.created"
        assert headers.signature == "abc123"
        assert headers.timestamp == "2024-01-01T00:00:00Z"

    def test_create_with_none_values(self) -> None:
        """WebhookHeaders can be created with None values."""
        headers = WebhookHeaders(
            event_id=None,
            event_type=None,
            signature=None,
            timestamp=None,
        )
        assert headers.event_id is None
        assert headers.event_type is None
        assert headers.signature is None
        assert headers.timestamp is None

    def test_create_with_partial_values(self) -> None:
        """WebhookHeaders can be created with partial values."""
        headers = WebhookHeaders(
            event_id="evt-123",
            event_type=None,
            signature=None,
            timestamp=None,
        )
        assert headers.event_id == "evt-123"
        assert headers.event_type is None

    def test_is_frozen(self) -> None:
        """WebhookHeaders is a frozen dataclass."""
        headers = WebhookHeaders(
            event_id="evt-123",
            event_type="user.created",
            signature="abc123",
            timestamp="2024-01-01T00:00:00Z",
        )
        with pytest.raises(AttributeError):
            headers.event_id = "changed"  # type: ignore


class TestExtractWebhookHeaders:
    """Tests for extract_webhook_headers function."""

    def test_extract_all_headers(self) -> None:
        """extract_webhook_headers extracts all standard headers."""
        headers = {
            "X-Webhook-Signature": "sig123",
            "X-Webhook-Event-Type": "user.created",
            "X-Webhook-Event-ID": "evt-123",
            "X-Webhook-Timestamp": "2024-01-01T00:00:00Z",
        }
        result = extract_webhook_headers(headers)
        assert result.signature == "sig123"
        assert result.event_type == "user.created"
        assert result.event_id == "evt-123"
        assert result.timestamp == "2024-01-01T00:00:00Z"

    def test_extract_missing_headers_returns_none(self) -> None:
        """extract_webhook_headers returns None for missing headers."""
        headers: dict[str, str] = {}
        result = extract_webhook_headers(headers)
        assert result.event_id is None
        assert result.event_type is None
        assert result.signature is None
        assert result.timestamp is None

    def test_extract_partial_headers(self) -> None:
        """extract_webhook_headers handles partial headers."""
        headers = {
            "X-Webhook-Signature": "sig123",
            "X-Webhook-Event-Type": "order.placed",
        }
        result = extract_webhook_headers(headers)
        assert result.signature == "sig123"
        assert result.event_type == "order.placed"
        assert result.event_id is None
        assert result.timestamp is None

    def test_extract_custom_header_names(self) -> None:
        """extract_webhook_headers supports custom header names."""
        headers = {
            "My-Signature": "sig123",
            "My-Event-Type": "user.created",
            "My-Event-ID": "evt-123",
            "My-Timestamp": "2024-01-01T00:00:00Z",
        }
        result = extract_webhook_headers(
            headers,
            signature_header="My-Signature",
            event_type_header="My-Event-Type",
            event_id_header="My-Event-ID",
            timestamp_header="My-Timestamp",
        )
        assert result.signature == "sig123"
        assert result.event_type == "user.created"
        assert result.event_id == "evt-123"
        assert result.timestamp == "2024-01-01T00:00:00Z"

    def test_extract_case_sensitive_headers(self) -> None:
        """extract_webhook_headers is case-sensitive."""
        headers = {
            "x-webhook-signature": "lowercase",
            "X-Webhook-Signature": "correctcase",
        }
        result = extract_webhook_headers(headers)
        assert result.signature == "correctcase"


class TestVerifyWebhookPayload:
    """Tests for verify_webhook_payload function."""

    @pytest.mark.asyncio
    async def test_verify_valid_payload(self) -> None:
        """verify_webhook_payload returns True for valid signature."""
        payload = b'{"event": "test"}'
        secret = "test-secret"
        
        from lexigram.webhook.verification.hmac import HMACSignatureVerifier
        verifier = HMACSignatureVerifier()
        signature = verifier.compute_signature(payload, secret)
        
        result = await verify_webhook_payload(payload, signature, secret)
        assert result is True

    @pytest.mark.asyncio
    async def test_verify_invalid_signature(self) -> None:
        """verify_webhook_payload returns False for invalid signature."""
        payload = b'{"event": "test"}'
        secret = "test-secret"
        
        result = await verify_webhook_payload(payload, "invalid-signature", secret)
        assert result is False

    @pytest.mark.asyncio
    async def test_verify_wrong_secret(self) -> None:
        """verify_webhook_payload returns False for wrong secret."""
        payload = b'{"event": "test"}'
        secret = "test-secret"
        
        from lexigram.webhook.verification.hmac import HMACSignatureVerifier
        verifier = HMACSignatureVerifier()
        signature = verifier.compute_signature(payload, "wrong-secret")
        
        result = await verify_webhook_payload(payload, signature, secret)
        assert result is False

    @pytest.mark.asyncio
    async def test_verify_tampered_payload(self) -> None:
        """verify_webhook_payload returns False for tampered payload."""
        payload = b'{"event": "test"}'
        secret = "test-secret"
        
        from lexigram.webhook.verification.hmac import HMACSignatureVerifier
        verifier = HMACSignatureVerifier()
        signature = verifier.compute_signature(payload, secret)
        
        tampered_payload = b'{"event": "hacked"}'
        result = await verify_webhook_payload(tampered_payload, signature, secret)
        assert result is False

    @pytest.mark.asyncio
    async def test_verify_empty_payload(self) -> None:
        """verify_webhook_payload handles empty payload."""
        payload = b""
        secret = "test-secret"
        
        result = await verify_webhook_payload(payload, "invalid", secret)
        assert result is False


class TestHelpersModuleExports:
    """Tests for module exports."""

    def test_all_contains_webhook_headers(self) -> None:
        """__all__ contains WebhookHeaders."""
        from lexigram.webhook.verification import helpers
        assert "WebhookHeaders" in helpers.__all__

    def test_all_contains_extract_webhook_headers(self) -> None:
        """__all__ contains extract_webhook_headers."""
        from lexigram.webhook.verification import helpers
        assert "extract_webhook_headers" in helpers.__all__

    def test_all_contains_verify_webhook_payload(self) -> None:
        """__all__ contains verify_webhook_payload."""
        from lexigram.webhook.verification import helpers
        assert "verify_webhook_payload" in helpers.__all__

    def test_module_imports(self) -> None:
        """Module can be imported."""
        from lexigram.webhook import verification
        assert verification.helpers is not None