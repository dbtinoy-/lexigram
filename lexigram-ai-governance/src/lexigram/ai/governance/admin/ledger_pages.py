"""Management page for the relay ledger top-up list.

The page is instantiated by the admin runtime from a dotted-path
handler; the ledger service is resolved from the DI container by
protocol.  It renders metadata only — reference, amount, status —
never keys or headers, and shows an explicit unavailable state when
the service is missing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from starlette.responses import HTMLResponse

from lexigram.logging import get_logger
from lexigram.ui import Card, Divider, el, render_to_string

if TYPE_CHECKING:
    from lexigram.contracts.ai.relay import RelayLedgerServiceProtocol

__all__ = ["RelayLedgerPage"]

logger = get_logger(__name__)

_PAGE_LIMIT = 50

_STATUS_COLORS = {
    "pending": "bg-yellow-100 text-yellow-700",
    "completed": "bg-green-100 text-green-700",
    "failed": "bg-red-100 text-red-700",
}


def _status_badge(status: str) -> Any:
    """Render a colored status badge for a top-up row."""
    return el(
        "span",
        status,
        class_=(
            f"inline-block px-2 py-0.5 rounded text-xs font-medium "
            f"{_STATUS_COLORS.get(status, 'bg-gray-100 text-gray-500')}"
        ),
    )


def _unavailable_page(title: str, reason: str) -> HTMLResponse:
    """Render a full page with an explicit unavailable dependency card."""
    html = render_to_string(
        el(
            "div",
            el(
                "h1",
                title,
                class_="text-2xl font-bold text-[var(--foreground)]",
            ),
            Divider(),
            Card(
                title="Unavailable",
                content=render_to_string(
                    el(
                        "p",
                        reason,
                        class_="text-sm text-[var(--muted-foreground)]",
                    )
                ),
            ),
        )
    )
    return HTMLResponse(html)


class RelayLedgerPage:
    """Management page at /admin/ai-governance/relay-ledger."""

    def __init__(self, service: RelayLedgerServiceProtocol | None = None) -> None:
        self._service = service

    async def handle(self, request: Any) -> HTMLResponse:
        """Render the ledger top-up list.

        Args:
            request: The starlette request.

        Returns:
            The rendered ledger page HTML.
        """
        if self._service is None:
            return _unavailable_page(
                "Relay Ledger",
                "The relay ledger requires the ledger service.",
            )
        try:
            topups = await self._service.list_topups(user_id=None, limit=_PAGE_LIMIT)
        except ValueError as exc:
            logger.warning("governance.ledger.list_rejected", error=str(exc))
            return _unavailable_page("Relay Ledger", str(exc))

        rows = [
            el(
                "tr",
                el(
                    "td",
                    topup.reference_id,
                    class_="py-1.5 pr-3 font-mono text-xs",
                ),
                el("td", topup.amount, class_="py-1.5 pr-3"),
                el("td", _status_badge(topup.status), class_="py-1.5"),
            )
            for topup in topups
        ]
        body = (
            rows
            if rows
            else el(
                "p",
                "No top-ups on the ledger yet.",
                class_="text-sm text-[var(--muted-foreground)] py-4",
            )
        )
        html = render_to_string(
            el(
                "div",
                el(
                    "h1",
                    "Relay Ledger",
                    class_="text-2xl font-bold text-[var(--foreground)]",
                ),
                Divider(),
                Card(
                    title="Top-Ups",
                    content=render_to_string(
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
                                            "Reference",
                                            class_=(
                                                "text-left text-xs font-semibold "
                                                "text-[var(--muted-foreground)] "
                                                "uppercase tracking-wider pb-1 pr-3"
                                            ),
                                            scope_="col",
                                        ),
                                        el(
                                            "th",
                                            "Amount",
                                            class_=(
                                                "text-left text-xs font-semibold "
                                                "text-[var(--muted-foreground)] "
                                                "uppercase tracking-wider pb-1 pr-3"
                                            ),
                                            scope_="col",
                                        ),
                                        el(
                                            "th",
                                            "Status",
                                            class_=(
                                                "text-left text-xs font-semibold "
                                                "text-[var(--muted-foreground)] "
                                                "uppercase tracking-wider pb-1 pr-3"
                                            ),
                                            scope_="col",
                                        ),
                                    ),
                                ),
                                el(
                                    "tbody",
                                    body,
                                    class_="divide-y divide-[var(--border)]",
                                ),
                                class_="w-full",
                            ),
                        )
                    ),
                ),
                el(
                    "p",
                    "Settle pending references and run daily check-ins "
                    "from the ledger admin actions.",
                    class_="text-xs text-[var(--muted-foreground)] mt-4",
                ),
            )
        )
        return HTMLResponse(html)
