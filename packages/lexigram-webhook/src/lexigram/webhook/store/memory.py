"""In-memory webhook store: implements both subscription and delivery protocols."""

from __future__ import annotations

from datetime import datetime

from lexigram.contracts.webhook.protocols import (
    WebhookDeliveryStoreProtocol,
    WebhookSubscriptionStoreProtocol,
)
from lexigram.contracts.webhook.types import (
    DeliveryAttempt,
    DeliveryStatus,
    WebhookSubscription,
)

__all__ = ["InMemoryWebhookStore"]


class InMemoryWebhookStore(
    WebhookSubscriptionStoreProtocol,
    WebhookDeliveryStoreProtocol,
):
    """In-memory implementation of both webhook store protocols.

    Implements ``WebhookSubscriptionStoreProtocol`` and
    ``WebhookDeliveryStoreProtocol``. Intended for testing and development
    only — data is not persisted across restarts.
    """

    def __init__(self) -> None:
        """Initialize empty in-memory stores."""
        self._subscriptions: dict[str, WebhookSubscription] = {}
        self._attempts: list[DeliveryAttempt] = []

    # --- WebhookSubscriptionStoreProtocol ---

    async def create(self, subscription: WebhookSubscription) -> None:
        """Persist a new subscription.

        Args:
            subscription: Subscription to store.
        """
        self._subscriptions[subscription.subscription_id] = subscription

    async def get(self, subscription_id: str) -> WebhookSubscription | None:
        """Return subscription by ID, or None.

        Args:
            subscription_id: UUID to look up.

        Returns:
            The subscription if found, else None.
        """
        return self._subscriptions.get(subscription_id)

    async def list(
        self,
        *,
        active_only: bool = True,
        event_type: str | None = None,
        tenant_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[WebhookSubscription]:
        """List subscriptions matching filters.

        Args:
            active_only: Only return active subscriptions.
            event_type: Filter to subscriptions that handle this event type.
            tenant_id: Filter by tenant.
            limit: Maximum results.
            offset: Results to skip.

        Returns:
            Filtered and paginated subscriptions.
        """
        results: list[WebhookSubscription] = []
        for sub in self._subscriptions.values():
            if active_only and not sub.active:
                continue
            if tenant_id is not None and sub.tenant_id != tenant_id:
                continue
            if event_type is not None and sub.event_types is not None:
                if event_type not in sub.event_types:
                    continue
            results.append(sub)
        return results[offset : offset + limit]

    async def update(self, subscription: WebhookSubscription) -> None:
        """Update an existing subscription.

        Args:
            subscription: Updated subscription data.
        """
        self._subscriptions[subscription.subscription_id] = subscription

    async def delete(self, subscription_id: str) -> None:
        """Remove a subscription.

        Args:
            subscription_id: UUID to remove.
        """
        self._subscriptions.pop(subscription_id, None)

    # --- WebhookDeliveryStoreProtocol ---

    async def record_attempt(self, attempt: DeliveryAttempt) -> None:
        """Persist a delivery attempt record.

        Args:
            attempt: Attempt to record.
        """
        self._attempts.insert(0, attempt)

    async def get_attempts(
        self,
        *,
        subscription_id: str | None = None,
        event_id: str | None = None,
        status: DeliveryStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DeliveryAttempt]:  # type: ignore[valid-type]
        """Query delivery attempts matching filters, newest-first.

        Args:
            subscription_id: Filter by subscription.
            event_id: Filter by event.
            status: Filter by delivery status.
            limit: Maximum results.
            offset: Results to skip.

        Returns:
            Matching attempts in newest-first order.
        """
        results: list[DeliveryAttempt] = []
        for attempt in self._attempts:
            if (
                subscription_id is not None
                and attempt.subscription_id != subscription_id
            ):
                continue
            if event_id is not None and attempt.event_id != event_id:
                continue
            if status is not None and attempt.status != status:
                continue
            results.append(attempt)
        return results[offset : offset + limit]

    async def get_dead_letters(
        self,
        *,
        subscription_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DeliveryAttempt]:  # type: ignore[valid-type]
        """Return attempts in dead-letter status.

        Args:
            subscription_id: Optional filter by subscription.
            limit: Maximum results.
            offset: Results to skip.

        Returns:
            Dead-lettered attempts.
        """
        return await self.get_attempts(
            subscription_id=subscription_id,
            status=DeliveryStatus.DEAD_LETTER,
            limit=limit,
            offset=offset,
        )

    async def count_recent_failures(
        self,
        subscription_id: str,
        since: datetime,
    ) -> int:
        """Count failed attempts for a subscription since a given time.

        Args:
            subscription_id: Subscription to check.
            since: Count attempts after this timestamp.

        Returns:
            Count of failed attempts.
        """
        failure_statuses = {DeliveryStatus.FAILED, DeliveryStatus.DEAD_LETTER}
        count = 0
        for attempt in self._attempts:
            if attempt.subscription_id != subscription_id:
                continue
            if attempt.status not in failure_statuses:
                continue
            if attempt.attempted_at >= since:
                count += 1
        return count
