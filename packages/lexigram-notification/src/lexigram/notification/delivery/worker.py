"""Retry worker for deferred mail deliveries.

Executes what :class:`~lexigram.notification.delivery.retry.RetryingMailer`
schedules: re-sends deliveries whose backoff window has elapsed and records
outcomes via the store.

Wire it to the task executor::

    executor.register_handler(
        "notification.flush_retries",
        lambda: flush_retries(store, backend),
    )
"""

from __future__ import annotations

from typing import Any

from lexigram.contracts.mailer import EmailMessage
from lexigram.logging import get_logger

logger = get_logger(__name__)

_MAX_ATTEMPTS = 5
"""Abandon a delivery after this many attempts."""


async def flush_retries(store: Any, backend: Any, limit: int = 50) -> int:
    """Re-send deferred deliveries whose backoff window has elapsed.

    Args:
        store: Delivery-state store exposing ``due_deliveries`` plus the
            ``DeliveryStoreProtocol`` mutation methods.
        backend: Raw mail backend used for the re-send attempts.
        limit: Maximum deliveries processed per flush.

    Returns:
        The number of deliveries completed during this flush.
    """

    due = await store.due_deliveries(limit)
    delivered = 0

    for entry in due:
        message_payload = entry.get("message") or {}
        recipient = entry.get("recipient", "")
        subject = str(message_payload.get("subject", ""))
        body = str(message_payload.get("body", ""))
        if not recipient or not subject:
            await store.mark_failed(entry["delivery_id"], "empty payload")
            continue

        message = EmailMessage(to=recipient.split(","), subject=subject, body=body)
        result = await backend.send(message)

        if result.is_ok():
            await store.mark_delivered(entry["delivery_id"])
            delivered += 1
            logger.info("retry_mail_delivered", delivery_id=entry["delivery_id"])
            continue

        attempts = int(entry.get("attempts", 0)) + 1
        error = str(result.unwrap_err())
        if attempts >= _MAX_ATTEMPTS:
            await store.mark_failed(entry["delivery_id"], reason=error)
            logger.error(
                "retry_mail_abandoned",
                delivery_id=entry["delivery_id"],
                attempts=attempts,
                error=error,
            )
        else:
            delay = min(60 * (2 ** max(0, attempts - 1)), 3600)
            await store.increment_retry(entry["delivery_id"])
            await store.schedule_retry(entry["delivery_id"], delay)
            logger.warning(
                "retry_mail_scheduled",
                delivery_id=entry["delivery_id"],
                attempts=attempts,
                delay_seconds=delay,
            )

    return delivered


__all__ = ["flush_retries"]
