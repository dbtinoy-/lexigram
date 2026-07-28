"""Webhook verification helper functions and data types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WebhookHeaders:
    """Parsed standard webhook headers from an inbound request.

    Attributes:
        event_id: Value of the event ID header.
        event_type: Value of the event type header.
        signature: Value of the signature header.
        timestamp: Value of the timestamp header.
    """

    event_id: str | None
    event_type: str | None
    signature: str | None
    timestamp: str | None


async def verify_webhook_payload(
    payload: bytes,
    signature_header: str,
    secret: str,
) -> bool:
    """Verify an inbound webhook payload using HMAC-SHA256.

    Convenience function for inbound webhook controllers.

    Args:
        payload: Raw request body bytes.
        signature_header: Value of the X-Webhook-Signature header.
        secret: Shared secret for this subscription.

    Returns:
        True if the signature is valid.
    """
    from lexigram.webhook.verification.hmac import HMACSignatureVerifier

    verifier = HMACSignatureVerifier()
    return verifier.verify(payload, signature_header, secret)


def extract_webhook_headers(
    headers: dict[str, str],
    *,
    signature_header: str = "X-Webhook-Signature",
    event_type_header: str = "X-Webhook-Event-Type",
    event_id_header: str = "X-Webhook-Event-ID",
    timestamp_header: str = "X-Webhook-Timestamp",
) -> WebhookHeaders:
    """Extract standard webhook headers from a request.

    Args:
        headers: Request headers dict (case-sensitive keys).
        signature_header: Header name for the signature.
        event_type_header: Header name for the event type.
        event_id_header: Header name for the event ID.
        timestamp_header: Header name for the timestamp.

    Returns:
        Parsed WebhookHeaders with extracted values (None if missing).
    """
    return WebhookHeaders(
        event_id=headers.get(event_id_header),
        event_type=headers.get(event_type_header),
        signature=headers.get(signature_header),
        timestamp=headers.get(timestamp_header),
    )


__all__ = [
    "WebhookHeaders",
    "extract_webhook_headers",
    "verify_webhook_payload",
]
