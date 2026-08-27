"""Webhook validator — validates incoming webhook requests."""

from __future__ import annotations

from typing import Any


class WebhookValidator:
    """Validates incoming webhook requests.

    Demonstrates webhook validation patterns with signature verification.
    """

    def __init__(self, signer: Any, max_payload_size: int = 1048576) -> None:
        self._signer = signer
        self._max_payload_size = max_payload_size

    def validate_payload_size(self, payload: bytes) -> bool:
        """Validate payload size is within limits."""
        return len(payload) <= self._max_payload_size

    def validate_signature(self, payload: bytes, signature: str | None) -> dict[str, Any]:
        """Validate webhook signature."""
        if not signature:
            return {"valid": False, "error": "Missing signature header"}

        if not self.validate_payload_size(payload):
            return {"valid": False, "error": "Payload too large"}

        if self._signer.verify(payload, signature):
            return {"valid": True}

        return {"valid": False, "error": "Invalid signature"}

    def validate_content_type(self, content_type: str | None) -> bool:
        """Validate content type is supported."""
        if not content_type:
            return False
        supported = ["application/json", "application/x-www-form-urlencoded"]
        return any(ct in content_type for ct in supported)
