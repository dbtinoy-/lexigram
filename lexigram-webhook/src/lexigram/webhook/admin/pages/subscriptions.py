from __future__ import annotations

from typing import Any

from lexigram.contracts.admin import PageContent
from lexigram.contracts.admin.widget_content import (
    EmptyContent,
    TableCell,
    TableContent,
)
from lexigram.contracts.webhook.protocols import (
    WebhookSubscriptionStoreProtocol,
)
from lexigram.logging.factory import get_logger

logger = get_logger(__name__)


class WebhookSubscriptionsPage:
    """Management page for /admin/webhooks/subscriptions."""

    def __init__(self, store: WebhookSubscriptionStoreProtocol | None = None) -> None:
        self._store = store

    async def handle(self, request: Any) -> PageContent:
        if self._store is None:
            return PageContent(
                title="Webhook Subscriptions",
                body=EmptyContent(
                    title="Webhook Store Unavailable",
                    message="The webhook subscription store could not be resolved.",
                    icon="webhook",
                ),
            )

        try:
            subs = await self._store.list(active_only=False, limit=1000)
        except Exception as exc:
            logger.warning("webhook_subscriptions.list_failed", error=str(exc))
            return PageContent(
                title="Webhook Subscriptions",
                body=EmptyContent(
                    title="Webhook Store Error",
                    message="Failed to retrieve webhook subscriptions.",
                    icon="webhook",
                ),
            )

        if not subs:
            return PageContent(
                title="Webhook Subscriptions",
                body=EmptyContent(
                    title="No Subscriptions",
                    message="No webhook subscriptions have been created yet.",
                    icon="webhook",
                ),
            )

        rows = tuple(
            (
                s.subscription_id[:8] + "...",
                s.url,
                "Active" if s.active else "Inactive",
                str(len(s.event_types or ())),
                s.created_at.strftime("%Y-%m-%d") if s.created_at else "-",
            )
            for s in subs
        )

        return PageContent(
            title="Webhook Subscriptions",
            body=TableContent(
                columns=("ID", "URL", "Status", "Events", "Created"),
                rows=tuple(tuple(TableCell(str(c)) for c in row) for row in rows),
            ),
        )
