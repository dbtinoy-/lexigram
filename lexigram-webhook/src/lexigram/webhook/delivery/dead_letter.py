"""Dead-letter queue manager for failed webhook deliveries."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.webhook.types import DeliveryAttempt
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.webhook.protocols import WebhookDeliveryStoreProtocol

logger = get_logger(__name__)

__all__ = ["DeadLetterManager"]


class DeadLetterManager:
    """Manages the dead-letter queue for failed webhook deliveries.

    Provides listing and count capabilities for dead-lettered
    webhook delivery attempts.
    """

    def __init__(self, delivery_store: WebhookDeliveryStoreProtocol) -> None:
        """Initialize the dead-letter manager.

        Args:
            delivery_store: Delivery attempt persistence backend.
        """
        self._store = delivery_store

    async def list(
        self,
        *,
        subscription_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DeliveryAttempt]:
        """List dead-lettered delivery attempts.

        Args:
            subscription_id: Optional subscription filter.
            limit: Page size.
            offset: Page offset.

        Returns:
            Dead-lettered attempts.
        """
        return await self._store.get_dead_letters(
            subscription_id=subscription_id,
            limit=limit,
            offset=offset,
        )

    async def count(self, subscription_id: str | None = None) -> int:
        """Count dead-lettered attempts.

        Args:
            subscription_id: Optional subscription filter.

        Returns:
            Count of dead-lettered attempts.
        """
        items = await self._store.get_dead_letters(
            subscription_id=subscription_id,
            limit=10000,
        )
        return len(items)
