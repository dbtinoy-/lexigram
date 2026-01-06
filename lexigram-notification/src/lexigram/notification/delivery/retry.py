"""RetryingMailer — wraps a mail backend with exponential backoff retry."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.logging import get_logger
from lexigram.notification.delivery.exceptions import PermanentDeliveryFailure
from lexigram.result import Err, Ok, Result

if TYPE_CHECKING:
    from lexigram.contracts.notification.delivery import DeliveryStoreProtocol

logger = get_logger(__name__)


class RetryingMailer:
    """Mail delivery wrapper with exponential backoff and async retry scheduling.

    Wraps any mail backend (one returning ``Result[Any, Any]``) with a delivery
    store that persists state and schedules deferred retries for transient
    failures — instead of sleeping in-process.

    Args:
        backend: The underlying mail backend with an async ``send()`` method
            returning ``Result[Any, Any]``.
        store: Delivery state store for tracking retry state.
        max_retries: Maximum delivery attempts before permanent failure.
        base_delay: Base delay in seconds for exponential backoff.
    """

    def __init__(
        self,
        backend: Any,
        store: DeliveryStoreProtocol,
        max_retries: int = 3,
        base_delay: float = 60.0,
    ) -> None:
        self._backend = backend
        self._store = store
        self._max_retries = max_retries
        self._base_delay = base_delay

    async def send(self, message: Any) -> Result[str, Any]:
        """Send a message, scheduling a retry on transient failure.

        Delegates to the backend. On ``Ok``, marks delivered. On ``Err``,
        increments the retry counter: if attempts are below ``max_retries``
        a deferred retry is scheduled via the store; otherwise the delivery
        is permanently failed.

        Args:
            message: Message to send (passed directly to ``backend.send()``).

        Returns:
            ``Ok(delivery_id)`` on success or when a retry has been scheduled.
            ``Err(PermanentDeliveryFailure)`` after max retries exhausted.
        """
        delivery_id = await self._store.create_pending(message)

        send_result = await self._backend.send(message)

        if send_result.is_ok():
            await self._store.mark_delivered(delivery_id)
            logger.info("mail_delivered", delivery_id=delivery_id)
            return Ok(delivery_id)

        attempt = await self._store.increment_retry(delivery_id)
        error = send_result.unwrap_err()

        if attempt < self._max_retries:
            delay = self._base_delay * (2 ** (attempt - 1))
            await self._store.schedule_retry(delivery_id, delay)
            logger.warning(
                "mail_delivery_retry_scheduled",
                delivery_id=delivery_id,
                attempt=attempt,
                delay_seconds=delay,
                error=str(error),
            )
            return Ok(delivery_id)

        await self._store.mark_failed(delivery_id, reason=str(error))
        logger.error(
            "mail_delivery_permanently_failed",
            delivery_id=delivery_id,
            attempts=attempt,
            error=str(error),
        )
        return Err(PermanentDeliveryFailure(delivery_id))


__all__ = ["RetryingMailer"]
