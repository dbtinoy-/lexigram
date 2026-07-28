"""HTTP delivery sender — executes a single webhook attempt."""

from __future__ import annotations

import uuid

import httpx

from lexigram.contracts.webhook.types import (
    DeliveryAttempt,
    DeliveryStatus,
    WebhookEvent,
    WebhookSubscription,
)
from lexigram.logging import get_logger
from lexigram.primitives import clock as ambient_clock
import lexigram.serialization as json
from lexigram.webhook.config import WebhookConfig
from lexigram.webhook.verification.hmac import HMACSignatureVerifier

logger = get_logger(__name__)

__all__ = ["WebhookSender"]


class WebhookSender:
    """Executes a single HTTP delivery attempt for one webhook subscription.

    Handles JSON serialization, HMAC signature computation, and
    structured attempt recording without raising exceptions on delivery failures.
    """

    def __init__(
        self,
        config: WebhookConfig,
        verifier: HMACSignatureVerifier | None = None,
    ) -> None:
        """Initialize the sender.

        Args:
            config: Webhook configuration (timeout, headers).
            verifier: HMAC verifier for signature computation.
                Defaults to ``HMACSignatureVerifier()``.
        """
        self._config = config
        self._verifier = verifier or HMACSignatureVerifier()

    async def send(
        self,
        event: WebhookEvent,
        subscription: WebhookSubscription,
        attempt_number: int = 1,
    ) -> DeliveryAttempt:
        """Send a single delivery attempt.

        Never raises — all failures are captured in the returned DeliveryAttempt.

        Args:
            event: Event to deliver.
            subscription: Target subscription.
            attempt_number: 1-based attempt counter.

        Returns:
            DeliveryAttempt with outcome details.
        """
        attempt_id = str(uuid.uuid4())
        payload_bytes = json.dumps(event.payload)
        signature = self._verifier.compute_signature(payload_bytes, subscription.secret)
        timestamp = ambient_clock.now().isoformat()

        headers = {
            "Content-Type": "application/json",
            self._config.signature_header: signature,
            self._config.event_type_header: event.event_type,
            self._config.event_id_header: event.event_id,
            self._config.timestamp_header: timestamp,
        }

        start = ambient_clock.monotonic()
        status_code: int | None = None
        error_message: str | None = None
        status = DeliveryStatus.FAILED

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    subscription.url,
                    content=payload_bytes,
                    headers=headers,
                    timeout=self._config.delivery_timeout_seconds,
                )
                status_code = response.status_code
                if 200 <= response.status_code < 300:
                    status = DeliveryStatus.DELIVERED
                else:
                    error_message = (
                        f"HTTP {response.status_code}: {response.text[:200]}"
                    )
        except Exception as exc:  # noqa: BLE001
            error_message = str(exc)

        duration_ms = (ambient_clock.monotonic() - start) * 1000

        return DeliveryAttempt(
            attempt_id=attempt_id,
            subscription_id=subscription.subscription_id,
            event_id=event.event_id,
            event_type=event.event_type,
            status=status,
            status_code=status_code,
            attempt_number=attempt_number,
            attempted_at=ambient_clock.now(),
            error_message=error_message,
            duration_ms=duration_ms,
        )
