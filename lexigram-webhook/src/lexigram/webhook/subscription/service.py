"""Webhook subscription service — CRUD with secret management."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
import uuid

from lexigram.contracts.webhook.types import WebhookSubscription
from lexigram.logging.factory import get_logger
from lexigram.result import Err, Ok, Result
from lexigram.webhook.config import WebhookConfig
from lexigram.webhook.exceptions import (
    InvalidWebhookURLError,
    SubscriptionNotFoundError,
)
from lexigram.webhook.subscription.secret import generate_webhook_secret

if TYPE_CHECKING:
    from lexigram.contracts.webhook.exceptions import WebhookError
    from lexigram.contracts.webhook.protocols import WebhookSubscriptionStoreProtocol

logger = get_logger(__name__)

__all__ = ["WebhookSubscriptionService"]


class WebhookSubscriptionService:
    """Service for managing webhook subscriptions.

    Provides create, read, update, delete operations for webhook
    subscriptions with secret management and URL validation.
    """

    def __init__(
        self,
        store: WebhookSubscriptionStoreProtocol,
        config: WebhookConfig,
    ) -> None:
        """Initialize the subscription service.

        Args:
            store: Subscription persistence backend.
            config: Webhook configuration.
        """
        self._store = store
        self._config = config

    async def create(
        self,
        url: str,
        *,
        event_types: frozenset[str] | None = None,
        description: str = "",
        tenant_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Result[WebhookSubscription, WebhookError]:
        """Create and persist a new webhook subscription.

        Args:
            url: HTTP(S) endpoint URL.
            event_types: Event type filter. None means all events.
            description: Human-readable label.
            tenant_id: Optional tenant scope.
            metadata: Arbitrary context data.

        Returns:
            Ok(subscription) on success, Err(InvalidWebhookURLError) if URL invalid.
        """
        if not url.startswith(("http://", "https://")):
            return Err(InvalidWebhookURLError(f"Invalid webhook URL: {url!r}"))

        subscription = WebhookSubscription(
            subscription_id=str(uuid.uuid4()),
            url=url,
            secret=generate_webhook_secret(self._config.secret_length),
            event_types=event_types,
            description=description,
            tenant_id=tenant_id,
            metadata=metadata or {},
        )
        await self._store.create(subscription)
        logger.info(
            "webhook_subscription_created",
            subscription_id=subscription.subscription_id,
            url=url,
        )
        return Ok(subscription)

    async def get(
        self, subscription_id: str
    ) -> Result[WebhookSubscription, WebhookError]:
        """Retrieve a subscription by ID.

        Args:
            subscription_id: UUID of the subscription.

        Returns:
            Ok(subscription) or Err(SubscriptionNotFoundError).
        """
        sub = await self._store.get(subscription_id)
        if sub is None:
            return Err(
                SubscriptionNotFoundError(f"Subscription not found: {subscription_id}")
            )
        return Ok(sub)

    async def list(
        self,
        *,
        event_type: str | None = None,
        tenant_id: str | None = None,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> list[WebhookSubscription]:
        """List subscriptions with optional filters.

        Args:
            event_type: Filter to subscriptions matching this event type.
            tenant_id: Filter by tenant.
            active_only: Only return active subscriptions.
            limit: Page size.
            offset: Page offset.

        Returns:
            List of matching subscriptions.
        """
        return await self._store.list(
            active_only=active_only,
            event_type=event_type,
            tenant_id=tenant_id,
            limit=limit,
            offset=offset,
        )

    async def update_event_types(
        self,
        subscription_id: str,
        event_types: frozenset[str] | None,
    ) -> Result[WebhookSubscription, WebhookError]:
        """Update the event type filter for a subscription.

        Args:
            subscription_id: Target subscription UUID.
            event_types: New event type filter. None = all events.

        Returns:
            Ok(updated_subscription) or Err(SubscriptionNotFoundError).
        """
        result = await self.get(subscription_id)
        if result.is_err():
            return result
        existing = result.unwrap()
        updated = WebhookSubscription(
            subscription_id=existing.subscription_id,
            url=existing.url,
            secret=existing.secret,
            event_types=event_types,
            active=existing.active,
            description=existing.description,
            tenant_id=existing.tenant_id,
            created_at=existing.created_at,
            metadata=existing.metadata,
        )
        await self._store.update(updated)
        return Ok(updated)

    async def rotate_secret(
        self, subscription_id: str
    ) -> Result[WebhookSubscription, WebhookError]:
        """Rotate the shared secret for a subscription.

        Stores the old secret in metadata["previous_secret"] with an expiry
        timestamp for the grace period. Both old and new secrets are valid
        during the grace period.

        Args:
            subscription_id: Target subscription UUID.

        Returns:
            Ok(updated_subscription) or Err on failure.
        """
        result = await self.get(subscription_id)
        if result.is_err():
            return result
        existing = result.unwrap()

        grace_expiry = datetime.now(UTC) + timedelta(
            hours=self._config.secret_rotation_grace_hours
        )
        new_metadata = dict(existing.metadata)
        new_metadata["previous_secret"] = existing.secret
        new_metadata["previous_secret_expires"] = grace_expiry.isoformat()

        updated = WebhookSubscription(
            subscription_id=existing.subscription_id,
            url=existing.url,
            secret=generate_webhook_secret(self._config.secret_length),
            event_types=existing.event_types,
            active=existing.active,
            description=existing.description,
            tenant_id=existing.tenant_id,
            created_at=existing.created_at,
            metadata=new_metadata,
        )
        await self._store.update(updated)
        logger.info("webhook_secret_rotated", subscription_id=subscription_id)
        return Ok(updated)

    async def deactivate(self, subscription_id: str) -> Result[None, WebhookError]:
        """Deactivate a subscription to stop receiving deliveries.

        Args:
            subscription_id: Target subscription UUID.

        Returns:
            Ok(None) or Err(SubscriptionNotFoundError).
        """
        result = await self.get(subscription_id)
        if result.is_err():
            return Err(result.unwrap_err())
        existing = result.unwrap()
        updated = WebhookSubscription(
            subscription_id=existing.subscription_id,
            url=existing.url,
            secret=existing.secret,
            event_types=existing.event_types,
            active=False,
            description=existing.description,
            tenant_id=existing.tenant_id,
            created_at=existing.created_at,
            metadata=existing.metadata,
        )
        await self._store.update(updated)
        logger.info("webhook_subscription_deactivated", subscription_id=subscription_id)
        return Ok(None)

    async def activate(self, subscription_id: str) -> Result[None, WebhookError]:
        """Reactivate a previously deactivated subscription.

        Args:
            subscription_id: Target subscription UUID.

        Returns:
            Ok(None) or Err(SubscriptionNotFoundError).
        """
        result = await self.get(subscription_id)
        if result.is_err():
            return Err(result.unwrap_err())
        existing = result.unwrap()
        updated = WebhookSubscription(
            subscription_id=existing.subscription_id,
            url=existing.url,
            secret=existing.secret,
            event_types=existing.event_types,
            active=True,
            description=existing.description,
            tenant_id=existing.tenant_id,
            created_at=existing.created_at,
            metadata=existing.metadata,
        )
        await self._store.update(updated)
        logger.info("webhook_subscription_activated", subscription_id=subscription_id)
        return Ok(None)
