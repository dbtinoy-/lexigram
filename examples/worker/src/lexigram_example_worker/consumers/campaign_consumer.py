"""Campaign queue consumer.

Subscribes to the ``campaigns.queued`` topic and dispatches incoming campaign
payloads to :class:`~lexigram_example_worker.tasks.send_email_batch.SendEmailBatchHandler`
in chunks matching the campaign's ``batch_size``.

Failed messages (handler returns ``Err``) are routed to the
:class:`~lexigram.queue.core.dlq.DeadLetterQueue` carried inside this
consumer so operators can inspect and re-publish them without losing data.

Patterns demonstrated:
- Subclass :class:`~lexigram.queue.consumer.MessageConsumer` for topic-scoped consumption
- Constructor injection for the handler and DLQ
- Dead letter routing on ``Result.is_err()``
- Retry counter in ``BusMessage.retry_count`` respected before DLQ routing
"""

from __future__ import annotations

from lexigram.contracts.queue.types import BusMessage
from lexigram.logging import get_logger
from lexigram.queue.consumers.consumer import MessageConsumer
from lexigram.queue.core.dlq import DeadLetterQueue

from lexigram_example_worker.domain.campaign import CampaignPayload
from lexigram_example_worker.tasks.send_email_batch import (
    EmailBatchPayload,
    SendEmailBatchHandler,
)

logger = get_logger(__name__)

# Topic this consumer subscribes to.
CAMPAIGN_TOPIC = "campaigns.queued"


class CampaignConsumer(MessageConsumer):
    """Processes incoming campaign messages and dispatches email batches.

    Extends :class:`~lexigram.queue.consumer.MessageConsumer` which handles
    subscription lifecycle and delegates each received message to
    :meth:`handle`.

    Receives its dependencies via constructor injection:

    - ``handler`` — performs the actual email send per batch
    - ``dlq`` — receives messages that exhaust their retry budget

    Args:
        queue: Queue backend to subscribe against (injected by framework).
        handler: Email batch handler (injected by :class:`~lexigram_example_worker.di.provider.WorkerProvider`).
        dlq: Dead letter queue for unrecoverable messages.
    """

    topic = CAMPAIGN_TOPIC

    def __init__(
        self,
        queue: object,  # QueueProtocol — typed as object to avoid coupling
        handler: SendEmailBatchHandler,
        dlq: DeadLetterQueue,
    ) -> None:
        super().__init__(queue)  # type: ignore[arg-type]
        self._handler = handler
        self._dlq = dlq

    async def handle(self, message: BusMessage) -> None:
        """Deserialise the message payload and dispatch email batches.

        Splits the campaign's recipient list into batches of ``batch_size``
        and calls :meth:`~lexigram_example_worker.tasks.send_email_batch.SendEmailBatchHandler.execute`
        for each slice.

        On ``Result.is_err()``:
        - If retries remain (``message.should_retry()``), the error is logged
          and the caller is expected to re-enqueue the message.
        - If the retry budget is exhausted the message is pushed to the
          :attr:`_dlq`.

        Args:
            message: Incoming ``BusMessage`` from the ``campaigns.queued`` topic.
        """
        logger.info(
            "campaign_consumer.received",
            message_id=message.id,
            retry_count=message.retry_count,
        )

        if not isinstance(message.payload, dict):
            error = f"Unexpected payload type: {type(message.payload).__name__}"
            logger.error("campaign_consumer.invalid_payload", error=error)
            await self._dlq.push(message, error)
            return

        try:
            campaign = CampaignPayload(**message.payload)
        except (TypeError, KeyError) as exc:
            error = f"Payload deserialisation failed: {exc}"
            logger.error(
                "campaign_consumer.deserialise_error",
                message_id=message.id,
                error=error,
            )
            await self._dlq.push(message, error)
            return

        # Chunk recipients into batches
        recipients = campaign.recipient_ids
        batch_size = max(1, campaign.batch_size)
        batches = [
            recipients[i : i + batch_size]
            for i in range(0, len(recipients), batch_size)
        ]

        logger.info(
            "campaign_consumer.dispatching",
            campaign_id=campaign.campaign_id,
            total_recipients=len(recipients),
            batch_count=len(batches),
        )

        for idx, batch in enumerate(batches):
            payload = EmailBatchPayload.from_campaign(campaign, batch)
            result = await self._handler.execute(payload)

            if result.is_ok():
                batch_result = result.unwrap()
                logger.info(
                    "campaign_consumer.batch_sent",
                    campaign_id=campaign.campaign_id,
                    batch_index=idx,
                    sent=batch_result.sent,
                    failed=len(batch_result.failed_ids),
                )
            else:
                error = str(result.unwrap_err())
                logger.warning(
                    "campaign_consumer.batch_failed",
                    campaign_id=campaign.campaign_id,
                    batch_index=idx,
                    error=error,
                    retries_remaining=message.max_retries - message.retry_count,
                )
                if not message.should_retry():
                    logger.error(
                        "campaign_consumer.dead_lettering",
                        message_id=message.id,
                        campaign_id=campaign.campaign_id,
                        error=error,
                    )
                    await self._dlq.push(message, error)


__all__ = ["CAMPAIGN_TOPIC", "CampaignConsumer"]
