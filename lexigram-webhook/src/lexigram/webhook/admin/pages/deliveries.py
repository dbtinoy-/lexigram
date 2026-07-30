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


class WebhookDeliveriesPage:
    """Management page for /admin/webhooks/deliveries."""

    def __init__(self, store: WebhookDeliveryStoreProtocol | None = None) -> None:
        self._store = store

    async def handle(self, request: Any) -> PageContent:
        if self._store is None:
            return PageContent(
                title="Webhook Deliveries",
                body=EmptyContent(
                    title="Webhook Store Unavailable",
                    message="The webhook delivery store could not be resolved.",
                    icon="webhook",
                ),
            )

        try:
            all_deliveries = await self._store.get_attempts(limit=500)
        except Exception as exc:
            logger.warning("webhook_deliveries.get_attempts_failed", error=str(exc))
            return PageContent(
                title="Webhook Deliveries",
                body=EmptyContent(
                    title="Webhook Store Error",
                    message="Failed to retrieve webhook deliveries.",
                    icon="webhook",
                ),
            )

        if not all_deliveries:
            return PageContent(
                title="Webhook Deliveries",
                body=EmptyContent(
                    title="No Deliveries",
                    message="No webhook deliveries have been recorded yet.",
                    icon="send",
                ),
            )

        rows = tuple(
            (
                d.event_type,
                d.subscription_id[:8] + "...",
                d.status.value,
                str(d.attempt_number),
                f"{d.duration_ms}ms" if d.duration_ms else "-",
                d.error_message or "-",
            )
            for d in all_deliveries[:50]
        )

        return PageContent(
            title="Webhook Deliveries",
            body=TableContent(
                columns=(
                    "Event",
                    "Subscription",
                    "Status",
                    "Attempt",
                    "Duration",
                    "Error",
                ),
                rows=tuple(tuple(TableCell(str(c)) for c in row) for row in rows),
            ),
        )
