"""Management page for the relay ledger top-up list.

The page is instantiated by the admin runtime from a dotted-path
handler; the ledger service is resolved from the DI container by
protocol.  It renders metadata only — reference, amount, status —
never keys or headers, and shows an explicit unavailable state when
the service is missing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.contracts.admin import PageContent
from lexigram.contracts.admin.widget_content import (
    EmptyContent,
    TableCell,
    TableContent,
)
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.ai.relay import RelayLedgerServiceProtocol

__all__ = ["RelayLedgerPage"]

logger = get_logger(__name__)

_PAGE_LIMIT = 50


def _unavailable_content(title: str, reason: str) -> PageContent:
    """Build a page with an explicit unavailable dependency state."""
    return PageContent(
        title=title,
        body=EmptyContent(
            title="Unavailable",
            message=reason,
            icon="alert-triangle",
        ),
    )


class RelayLedgerPage:
    """Management page at /admin/ai-governance/relay-ledger."""

    def __init__(self, service: RelayLedgerServiceProtocol | None = None) -> None:
        self._service = service

    async def handle(self, request: Any) -> PageContent:
        """Render the ledger top-up list.

        Args:
            request: The starlette request.

        Returns:
            The structured ledger page content.
        """
        del request
        if self._service is None:
            return _unavailable_content(
                "Relay Ledger",
                "The relay ledger requires the ledger service.",
            )
        try:
            topups = await self._service.list_topups(user_id=None, limit=_PAGE_LIMIT)
        except ValueError as exc:
            logger.warning("governance.ledger.list_rejected", error=str(exc))
            return _unavailable_content("Relay Ledger", str(exc))

        if not topups:
            return PageContent(
                title="Relay Ledger",
                body=EmptyContent(
                    title="No top-ups on the ledger yet.",
                    icon="inbox",
                ),
            )
        return PageContent(
            title="Relay Ledger",
            body=TableContent(
                columns=("Reference", "Amount", "Status"),
                rows=tuple(
                    (
                        TableCell(topup.reference_id),
                        TableCell(str(topup.amount)),
                        TableCell(topup.status),
                    )
                    for topup in topups
                ),
            ),
        )
