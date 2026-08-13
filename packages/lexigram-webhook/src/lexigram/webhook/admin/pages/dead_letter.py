from __future__ import annotations

from typing import Any

from lexigram.contracts.admin import PageContent
from lexigram.contracts.admin.widget_content import (
    EmptyContent,
    TableCell,
    TableContent,
)
from lexigram.contracts.webhook.protocols import (
    WebhookDeliveryStoreProtocol,
)
from lexigram.logging.factory import get_logger

logger = get_logger(__name__)


class WebhookDeadLetterPage:
    """Management page for /admin/webhooks/dead-letters."""

    def __init__(self, store: WebhookDeliveryStoreProtocol | None = None) -> None:
        self._store = store

    async def handle(self, request: Any) -> PageContent:
        if self._store is None:
            return PageContent(
                title="Dead Letter Queue",
                body=EmptyContent(
                    title="Webhook Store Unavailable",
                    message="The webhook delivery store could not be resolved.",
                    icon="webhook",
                ),
            )

        try:
            dead = await self._store.get_dead_letters(limit=500)
        except Exception as exc:
            logger.warning("webhook_dead_letters.get_failed", error=str(exc))
            return PageContent(
                title="Dead Letter Queue",
                body=EmptyContent(
                    title="Webhook Store Error",
                    message="Failed to retrieve dead letters.",
                    icon="alert-triangle",
                ),
            )

        if not dead:
            return PageContent(
                title="Dead Letter Queue",
                body=EmptyContent(
                    title="No Dead Letters",
                    message="No webhook deliveries have been dead-lettered.",
                    icon="alert-triangle",
                ),
            )

        rows = tuple(
            (
                d.event_type,
                d.subscription_id[:8] + "...",
                str(d.attempt_number),
                d.error_message or "-",
                d.attempted_at.strftime("%Y-%m-%d %H:%M") if d.attempted_at else "-",
            )
            for d in dead
        )

        return PageContent(
            title="Dead Letter Queue",
            body=TableContent(
                columns=(
                    "Event Type",
                    "Subscription",
                    "Attempts",
                    "Last Error",
                    "Last Attempt",
                ),
                rows=tuple(tuple(TableCell(str(c)) for c in row) for row in rows),
            ),
        )
