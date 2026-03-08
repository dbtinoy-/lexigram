from __future__ import annotations

from typing import Any

from starlette.responses import HTMLResponse

from lexigram.contracts.webhook.protocols import (
    WebhookSubscriptionStoreProtocol,
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

logger = get_logger(__name__)


class WebhookSubscriptionsPage:
    """Management page for /admin/webhooks/subscriptions."""

    def __init__(self, store: WebhookSubscriptionStoreProtocol | None = None) -> None:
        self._store = store

    async def handle(self, request: Any) -> HTMLResponse:
        if self._store is None:
            html = render_to_string(
                EmptyState(
                    title="Webhook Store Unavailable",
                    message="The webhook subscription store could not be resolved.",
                    icon="webhook",
                ),
            )
            return HTMLResponse(html)

        try:
            subs = await self._store.list(active_only=False, limit=1000)
        except Exception as exc:
            logger.warning("webhook_subscriptions.list_failed", error=str(exc))
            html = render_to_string(
                EmptyState(
                    title="Webhook Store Error",
                    message="Failed to retrieve webhook subscriptions.",
                    icon="webhook",
                ),
            )
            return HTMLResponse(html)

        if not subs:
            html = render_to_string(
                EmptyState(
                    title="No Subscriptions",
                    message="No webhook subscriptions have been created yet.",
                    icon="webhook",
                ),
            )
            return HTMLResponse(html)

        total = len(subs)
        active = sum(1 for s in subs if s.active)
        inactive = total - active

        html = render_to_string(
            el(
                "div",
                el(
                    "h1",
                    "Webhook Subscriptions",
                    class_="text-2xl font-bold text-[var(--foreground)]",
                ),
                el(
                    "p",
                    "Manage webhook subscriptions and endpoints.",
                    class_="text-sm text-[var(--muted-foreground)] mt-1 mb-6",
                ),
                Divider(),
                Grid(
                    StatCard(label="Total", value=str(total), icon="webhook"),
                    StatCard(
                        label="Active",
                        value=str(active),
                        delta_color="green",
                        icon="check-circle",
                    ),
                    StatCard(
                        label="Inactive",
                        value=str(inactive),
                        delta_color="red",
                        icon="x-circle",
                    ),
                    cols={"default": 1, "lg": 3},
                    gap=4,
                    class_="mb-6 mt-6",
                ),
                el(
                    "h2",
                    "All Subscriptions",
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
                                    "ID",
                                    style="width:25%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                                el(
                                    "th",
                                    "URL",
                                    style="width:35%",
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
                                    "Events",
                                    style="width:15%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                                el(
                                    "th",
                                    "Created",
                                    style="width:10%",
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
                                        s.subscription_id[:8] + "...",
                                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--foreground)]",
                                    ),
                                    el(
                                        "td",
                                        s.url,
                                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--foreground)] font-mono max-w-[300px] truncate",
                                    ),
                                    el(
                                        "td",
                                        Badge(
                                            "Active" if s.active else "Inactive",
                                            variant="success"
                                            if s.active
                                            else "default",
                                        ),
                                        class_="px-4 py-3 whitespace-nowrap text-sm",
                                    ),
                                    el(
                                        "td",
                                        str(len(s.event_types or ())),
                                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--foreground)]",
                                    ),
                                    el(
                                        "td",
                                        s.created_at.strftime("%Y-%m-%d")
                                        if s.created_at
                                        else "-",
                                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--muted-foreground)]",
                                    ),
                                )
                                for s in subs
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
