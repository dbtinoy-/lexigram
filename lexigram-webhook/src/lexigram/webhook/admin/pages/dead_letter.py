from __future__ import annotations

from typing import Any

from starlette.responses import HTMLResponse

from lexigram.contracts.webhook.protocols import (
    WebhookDeliveryStoreProtocol,
)
from lexigram.logging.factory import get_logger
from lexigram.ui.atoms.divider import Divider
from lexigram.ui.atoms.layout import Grid
from lexigram.ui.core.base import el, render_to_string
from lexigram.ui.molecules.empty_state import EmptyState
from lexigram.ui.molecules.stat_card import StatCard

logger = get_logger(__name__)


class WebhookDeadLetterPage:
    """Management page for /admin/webhooks/dead-letters."""

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
            dead = await self._store.get_dead_letters(limit=500)
        except Exception as exc:
            logger.warning("webhook_dead_letters.get_failed", error=str(exc))
            html = render_to_string(
                EmptyState(
                    title="Webhook Store Error",
                    message="Failed to retrieve dead letters.",
                    icon="alert-triangle",
                ),
            )
            return HTMLResponse(html)

        if not dead:
            html = render_to_string(
                EmptyState(
                    title="No Dead Letters",
                    message="No webhook deliveries have been dead-lettered.",
                    icon="alert-triangle",
                ),
            )
            return HTMLResponse(html)

        html = render_to_string(
            el(
                "div",
                el(
                    "h1",
                    "Dead Letter Queue",
                    class_="text-2xl font-bold text-[var(--foreground)]",
                ),
                el(
                    "p",
                    "Webhook deliveries that have exhausted all retry attempts.",
                    class_="text-sm text-[var(--muted-foreground)] mt-1 mb-6",
                ),
                Divider(),
                Grid(
                    StatCard(
                        label="Dead Letters",
                        value=str(len(dead)),
                        icon="alert-triangle",
                    ),
                    cols={"default": 1, "lg": 1},
                    gap=4,
                    class_="mb-6 mt-6",
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
                                    "Event Type",
                                    style="width:18%",
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
                                    "Attempts",
                                    style="width:10%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                                el(
                                    "th",
                                    "Last Error",
                                    style="width:40%",
                                    class_="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] bg-[var(--card)] sticky top-0 z-10",
                                ),
                                el(
                                    "th",
                                    "Last Attempt",
                                    style="width:17%",
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
                                        str(d.attempt_number),
                                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--foreground)]",
                                    ),
                                    el(
                                        "td",
                                        d.error_message or "-",
                                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--muted-foreground)] max-w-[250px] truncate",
                                    ),
                                    el(
                                        "td",
                                        d.attempted_at.strftime("%Y-%m-%d %H:%M")
                                        if d.attempted_at
                                        else "-",
                                        class_="px-4 py-3 whitespace-nowrap text-sm text-[var(--muted-foreground)]",
                                    ),
                                )
                                for d in dead
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
