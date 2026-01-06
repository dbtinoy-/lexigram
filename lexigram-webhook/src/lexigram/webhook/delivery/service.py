"""Webhook delivery orchestration — retry, dead-letter, and auto-disable."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from lexigram.contracts.webhook.types import (
    DeliveryAttempt,
    DeliveryStatus,
    WebhookEvent,
    WebhookSubscription,
)
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result
from lexigram.webhook.config import WebhookConfig
from lexigram.webhook.delivery.sender import WebhookSender
from lexigram.webhook.exceptions import (
    DeliveryAttemptNotFoundError,
    SubscriptionNotFoundError,
)

if TYPE_CHECKING:
    from lexigram.contracts.webhook.exceptions import WebhookError
    from lexigram.contracts.webhook.protocols import (
        WebhookDeliveryStoreProtocol,
        WebhookSubscriptionStoreProtocol,
    )

logger = get_logger(__name__)

__all__ = ["WebhookDeliveryService"]


class WebhookDeliveryService:
    """Orchestrates webhook event delivery with retry and dead-letter logic.

    Implements ``WebhookDeliveryServiceProtocol``.
    """

    def __init__(
        self,
        subscription_store: WebhookSubscriptionStoreProtocol,
        delivery_store: WebhookDeliveryStoreProtocol,
        sender: WebhookSender,
        config: WebhookConfig,
    ) -> None:
        """Initialize the delivery service.

        Args:
            subscription_store: Subscription persistence backend.
            delivery_store: Delivery attempt persistence backend.
            sender: HTTP sender for individual attempts.
            config: Webhook configuration.
        """
        self._subscription_store = subscription_store
        self._delivery_store = delivery_store
        self._sender = sender
        self._config = config

    async def dispatch(self, event: WebhookEvent) -> None:
        """Deliver an event to all matching active subscriptions.

        Fan-out to all matching subscriptions concurrently. Each delivery
        runs with retry. Errors per subscription are logged but do not
        affect other subscriptions.

        Args:
            event: Event to deliver.
        """
        subscriptions = await self._subscription_store.list(
            active_only=True,
            event_type=event.event_type,
        )
        if not subscriptions:
            logger.debug("webhook_no_subscribers", event_type=event.event_type)
            return

        tasks = [
            asyncio.create_task(self._deliver_with_retry(event, sub))
            for sub in subscriptions
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for sub, task_result in zip(subscriptions, results, strict=True):
            if isinstance(task_result, Exception):
                logger.error(
                    "webhook_delivery_task_failed",
                    subscription_id=sub.subscription_id,
                    error=str(task_result),
                )

    async def redeliver(self, attempt_id: str) -> Result[None, WebhookError]:
        """Redeliver a failed or dead-lettered attempt.

        Args:
            attempt_id: ID of the attempt to redeliver.

        Returns:
            Ok(None) on success, Err on failure.
        """
        attempts = await self._delivery_store.get_attempts(limit=10000)
        original: DeliveryAttempt | None = None
        for a in attempts:
            if a.attempt_id == attempt_id:
                original = a
                break

        if original is None:
            return Err(DeliveryAttemptNotFoundError(f"Attempt not found: {attempt_id}"))

        sub = await self._subscription_store.get(original.subscription_id)
        if sub is None:
            return Err(
                SubscriptionNotFoundError(
                    f"Subscription not found: {original.subscription_id}"
                )
            )

        event = WebhookEvent(
            event_id=original.event_id,
            event_type=original.event_type,
            payload={},
        )
        new_attempt = await self._sender.send(
            event, sub, attempt_number=original.attempt_number + 1
        )
        await self._delivery_store.record_attempt(new_attempt)
        logger.info(
            "webhook_redelivered",
            original_attempt_id=attempt_id,
            new_attempt_id=new_attempt.attempt_id,
        )
        return Ok(None)

    async def _deliver_with_retry(
        self,
        event: WebhookEvent,
        subscription: WebhookSubscription,
    ) -> None:
        """Deliver to one subscription with exponential backoff retry.

        Escalates to DEAD_LETTER after max_attempts.

        Args:
            event: Event to deliver.
            subscription: Target subscription.
        """
        delay = self._config.retry_base_delay
        for attempt_number in range(1, self._config.retry_max_attempts + 1):
            attempt = await self._sender.send(
                event, subscription, attempt_number=attempt_number
            )

            if attempt.status == DeliveryStatus.DELIVERED:
                await self._delivery_store.record_attempt(attempt)
                logger.info(
                    "webhook_delivered",
                    subscription_id=subscription.subscription_id,
                    event_id=event.event_id,
                    attempt=attempt_number,
                )
                return

            is_last = attempt_number >= self._config.retry_max_attempts
            if is_last:
                dead_letter = DeliveryAttempt(
                    attempt_id=attempt.attempt_id,
                    subscription_id=attempt.subscription_id,
                    event_id=attempt.event_id,
                    event_type=attempt.event_type,
                    status=DeliveryStatus.DEAD_LETTER,
                    status_code=attempt.status_code,
                    attempt_number=attempt.attempt_number,
                    attempted_at=attempt.attempted_at,
                    error_message=attempt.error_message,
                    duration_ms=attempt.duration_ms,
                )
                await self._delivery_store.record_attempt(dead_letter)
                logger.warning(
                    "webhook_dead_lettered",
                    subscription_id=subscription.subscription_id,
                    event_id=event.event_id,
                )
                await self._check_auto_disable(subscription)
            else:
                await self._delivery_store.record_attempt(attempt)
                logger.warning(
                    "webhook_delivery_failed_retrying",
                    subscription_id=subscription.subscription_id,
                    event_id=event.event_id,
                    attempt=attempt_number,
                    next_delay=delay,
                )
                await asyncio.sleep(delay)
                delay = min(
                    delay * self._config.retry_backoff_factor,
                    self._config.retry_max_delay,
                )

    async def _check_auto_disable(self, subscription: WebhookSubscription) -> None:
        """Auto-disable a subscription if it has exceeded the failure threshold.

        Args:
            subscription: Subscription to check.
        """
        window_start = datetime.now(UTC) - timedelta(
            hours=self._config.failure_window_hours
        )
        failure_count = await self._delivery_store.count_recent_failures(
            subscription.subscription_id,
            since=window_start,
        )
        if failure_count >= self._config.disable_after_consecutive_failures:
            updated = WebhookSubscription(
                subscription_id=subscription.subscription_id,
                url=subscription.url,
                secret=subscription.secret,
                event_types=subscription.event_types,
                active=False,
                description=subscription.description,
                tenant_id=subscription.tenant_id,
                created_at=subscription.created_at,
                metadata=subscription.metadata,
            )
            await self._subscription_store.update(updated)
            logger.warning(
                "webhook_subscription_auto_disabled",
                subscription_id=subscription.subscription_id,
                failure_count=failure_count,
            )
