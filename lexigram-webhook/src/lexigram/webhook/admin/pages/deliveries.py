from __future__ import annotations

from typing import Any

from starlette.responses import HTMLResponse

from lexigram.contracts.webhook.protocols import (
    WebhookDeliveryStoreProtocol,
)
from lexigram.logging import get_logger
from lexigram.ui import (
    Badge,
    Divider,
    EmptyState,
    Grid,
    StatCard,
    el,
    render_to_string,
)
from lexigram.ui.atoms.badge import BadgeVariant

logger = get_logger(__name__)


class WebhookDeliveriesPage:
    """Management page for /admin/webhooks/deliveries."""

    def __init__(self, store: WebhookDeliveryStoreProtocol | None = None) -> None:
        self._store = store

    async def handle(self, request: Any) -> HTMLResponse:
        if self._store is None:
            html = render_to_string(
                EmptyState(
                    title="Webhook Store Unavailable",
                    message="The webhook delivery store could not be resolved.",
                    icon="webhook",
                ),
            )
            return HTMLResponse(html)

        try:
            all_deliveries = await self._store.get_attempts(limit=500)
        except Exception as exc:
            logger.warning("webhook_deliveries.get_attempts_failed", error=str(exc))
            html = render_to_string(
                EmptyState(
                    title="Webhook Store Error",
                    message="Failed to retrieve webhook deliveries.",
                    icon="webhook",
                ),
            )
            return HTMLResponse(html)

        if not all_deliveries:
            html = render_to_string(
                EmptyState(
                    title="No Deliveries",
                    message="No webhook deliveries have been recorded yet.",
                    icon="send",
                ),
            )
            return HTMLResponse(html)

        total = len(all_deliveries)
        successful = sum(1 for d in all_deliveries if d.status.value == "delivered")
        failed = sum(1 for d in all_deliveries if d.status.value == "failed")
        dead = sum(1 for d in all_deliveries if d.status.value == "dead_letter")

        def _badge_variant(status: str) -> BadgeVariant:
            if status == "delivered":
                return "success"
            if status in ("failed", "dead_letter"):
                return "danger"
            return "warning"

        html = render_to_string(
            el(
                "div",
                el(
                    "h1",
                    "Webhook Deliveries",
                    class_="text-2xl font-bold text-[var(--foreground)]",
                ),
                el(
                    "p",
                    "Recent webhook delivery attempts and status.",
                    class_="text-sm text-[var(--muted-foreground)] mt-1 mb-6",
                ),
                Divider(),
                Grid(
                    StatCard(label="Total", value=str(total), icon="send"),
                    StatCard(
                        label="Delivered",
                        value=str(successful),
                        delta_color="green",
                        icon="check-circle",
                    ),
                    StatCard(
                        label="Failed",
                        value=str(failed),
                        delta_color="red",
                        icon="x-circle",
                    ),
                    StatCard(
                        label="Dead Letter",
                        value=str(dead),
                        delta_color="red",
                        icon="alert-triangle",
                    ),
                    cols={"default": 2, "lg": 4},
                    gap=4,
                    class_="mb-6 mt-6",
                ),
                el(
                    "h2",
                    "Recent Deliveries",
                    class_="text-lg font-semibold text-[var(--foreground)] mb-3",
                ),
                el(
                    "div",
                    el(
                        "table",
                        el(
                            "thead",
                            el(
                                "tr",
                                el(
                                    "th",
                                    "Event",
                                    style="width:20%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                                el(
                                    "th",
                                    "Subscription",
                                    style="width:15%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                                el(
                                    "th",
                                    "Status",
                                    style="width:15%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                                el(
                                    "th",
                                    "Attempt",
                                    style="width:10%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                                el(
                                    "th",
                                    "Duration",
                                    style="width:10%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                                el(
                                    "th",
                                    "Error",
                                    style="width:30%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                            ),
                        ),
                        el(
                            "tbody",
                            *[
                                el(
                                    "tr",
                                    el(
                                        "td",
                                        d.event_type,
                                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--foreground)]",
                                    ),
                                    el(
                                        "td",
                                        d.subscription_id[:8] + "...",
                                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--muted-foreground)] font-mono",
                                    ),
                                    el(
                                        "td",
                                        Badge(
                                            d.status.value,
                                            variant=_badge_variant(d.status.value),
                                        ),
                                        class_="px-4 py-3 whitespace-nowrap text-sm",
                                    ),
                                    el(
                                        "td",
                                        str(d.attempt_number),
                                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--foreground)]",
                                    ),
                                    el(
                                        "td",
                                        f"{d.duration_ms}ms" if d.duration_ms else "-",
                                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--muted-foreground)]",
                                    ),
                                    el(
                                        "td",
                                        d.error_message or "-",
                                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--muted-foreground)] max-w-[200px] truncate",
                                    ),
                                )
                                for d in all_deliveries[:50]
                            ],
                            class_="divide-y divide-[var(--border)]",
                        ),
                        class_="min-w-full table-fixed divide-y divide-[var(--border)]",
                    ),
                    class_="overflow-x-auto rounded-xl border border-[var(--border)] bg-[var(--card)]",
                ),
                class_="p-6",
            ),
        )

        return HTMLResponse(html)
