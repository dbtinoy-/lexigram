"""Management pages for the AI governance admin contributor.

Pages are instantiated by the admin runtime from dotted-path handlers;
dependencies are resolved from the DI container.  Every page renders an
explicit unavailable state when a dependency is missing and never
injects unescaped values.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from lexigram.ai.governance.relay_billing import (
    RelayReservationManager,
    RelayUsageReport,
    RelayUsageReportService,
)
from lexigram.contracts.admin import PageContent, PaginationContent
from lexigram.contracts.admin.widget_content import (
    EmptyContent,
    Stat,
    StatContent,
    TableCell,
    TableContent,
)
from lexigram.contracts.ai.governance import (
    RelayUsageStoreProtocol,
)
from lexigram.logging import get_logger
from lexigram.primitives import clock

__all__ = [
    "GovernanceQuotasPage",
    "GovernanceRelaySettlementsPage",
    "GovernanceRelayUsagePage",
]

logger = get_logger(__name__)

_DEFAULT_HOURS = 24
_PAGE_SIZE = 20


def _page(request: Any) -> tuple[int, int, int]:
    """Extract pagination and window parameters from a request.

    Args:
        request: The starlette request or stand-in.

    Returns:
        A ``(page, page_size, hours)`` tuple with safe defaults.
    """
    raw = getattr(request, "query_params", {})
    page = _as_int(raw.get("page"), 1, minimum=1)
    page_size = _as_int(raw.get("page_size"), _PAGE_SIZE, minimum=1)
    hours = _as_int(raw.get("hours"), _DEFAULT_HOURS, minimum=1)
    return page, page_size, hours


def _as_int(value: object, default: int, *, minimum: int) -> int:
    """Parse *value* as an integer, falling back on failure."""
    if not isinstance(value, str):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, parsed)


def _window(hours: int) -> tuple[datetime, datetime]:
    """Return the UTC start/end window for the last *hours* hours."""
    end = clock.now()
    return end - timedelta(hours=hours), end


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


def _usage_rows(report: RelayUsageReport) -> list[tuple[Any, ...]]:
    """Build table rows for a usage report page."""
    rows: list[tuple[Any, ...]] = []
    for record in report.rows:
        rows.append(
            (
                record.request_id,
                record.scope.tenant_id,
                record.scope.user_id or "-",
                record.scope.model or "-",
                str(record.usage.total_tokens),
                f"{record.charge:.4f}",
                record.status,
                ", ".join(record.loss_codes) or "-",
            )
        )
    return rows


class GovernanceRelayUsagePage:
    """Management page at /admin/ai-governance/relay-usage."""

    def __init__(self, store: RelayUsageStoreProtocol | None = None) -> None:
        self._reporter = RelayUsageReportService(store) if store is not None else None

    async def handle(self, request: Any) -> PageContent:
        """Render a paginated relay usage report for the window.

        Args:
            request: The starlette request.

        Returns:
            The structured usage report page content.
        """
        page, page_size, hours = _page(request)
        if self._reporter is None:
            return _unavailable_content(
                "Relay Usage",
                "Usage reporting requires the relay billing store.",
            )
        start, end = _window(hours)
        try:
            report = await self._reporter.report(
                start=start,
                end=end,
                page=page,
                page_size=page_size,
            )
        except ValueError as exc:
            logger.warning("governance.usage.window_rejected", error=str(exc))
            return _unavailable_content("Relay Usage", str(exc))

        if not report.rows:
            return PageContent(
                title="Relay Usage",
                body=EmptyContent(
                    title="No relay usage in this window.",
                    icon="inbox",
                ),
            )
        return PageContent(
            title="Relay Usage",
            body=TableContent(
                columns=(
                    "Request",
                    "Tenant",
                    "User",
                    "Model",
                    "Tokens",
                    "Charge",
                    "Status",
                    "Loss Codes",
                ),
                rows=tuple(
                    tuple(TableCell(str(cell)) for cell in row)
                    for row in _usage_rows(report)
                ),
            ),
            pagination=PaginationContent(
                page=page,
                total=report.total_rows,
                per_page=page_size,
                base_url=str(request.url).split("?")[0],
            ),
        )


class GovernanceQuotasPage:
    """Management page at /admin/ai-governance/relay-quotas."""

    def __init__(self, manager: RelayReservationManager | None = None) -> None:
        self._manager = manager

    async def handle(self, request: Any) -> PageContent:
        """Render current quota pressure per configured dimension.

        Args:
            request: The starlette request.

        Returns:
            The structured quota pressure page content.
        """
        del request
        if self._manager is None:
            return _unavailable_content(
                "Relay Quotas",
                "Quota reporting requires the reservation manager.",
            )
        snapshot = await self._manager.quota_snapshot()
        stats: list[Stat] = []
        for entry in (
            snapshot.tenant,
            snapshot.account,
            snapshot.user,
            snapshot.model,
            snapshot.provider,
            snapshot.channel,
        ):
            if entry is None:
                continue
            stats.append(
                Stat(
                    label=f"{entry.dimension.title()} — {entry.value}",
                    value=(
                        f"{entry.used_tokens:,} / {entry.max_tokens:,} tokens · "
                        f"{entry.used_charge:.4f} / {entry.max_charge:.4f} charge · "
                        f"remaining {entry.remaining_tokens():,} tokens · "
                        f"{entry.remaining_charge():.4f} charge"
                    ),
                )
            )
        if not stats:
            return PageContent(
                title="Relay Quotas",
                body=EmptyContent(
                    title="No quota limits configured; every dimension is unlimited.",
                    icon="inbox",
                ),
            )
        return PageContent(
            title="Relay Quotas",
            body=StatContent(stats=tuple(stats)),
        )


class GovernanceSettlementsPage:
    """Management page at /admin/ai-governance/relay-settlements."""

    def __init__(self, store: RelayUsageStoreProtocol | None = None) -> None:
        self._reporter = RelayUsageReportService(store) if store is not None else None

    async def handle(self, request: Any) -> PageContent:
        """Render settlement failures as table rows plus counts.

        Args:
            request: The starlette request.

        Returns:
            The structured settlement view page content.
        """
        page, page_size, hours = _page(request)
        if self._reporter is None:
            return _unavailable_content(
                "Relay Settlements",
                "Settlement reporting requires the relay billing store.",
            )
        start, end = _window(hours)
        report = await self._reporter.report(
            start=start,
            end=end,
            page=page,
            page_size=page_size,
            status="failed",
        )
        if not report.rows:
            return PageContent(
                title="Relay Settlements",
                body=EmptyContent(
                    title="No failed settlements in this window.",
                    icon="inbox",
                ),
            )
        return PageContent(
            title="Relay Settlements",
            body=TableContent(
                columns=(
                    "Request",
                    "Tenant",
                    "User",
                    "Model",
                    "Tokens",
                    "Charge",
                    "Status",
                    "Loss Codes",
                ),
                rows=tuple(
                    tuple(TableCell(str(cell)) for cell in row)
                    for row in _usage_rows(report)
                ),
            ),
            pagination=PaginationContent(
                page=page,
                total=report.total_rows,
                per_page=page_size,
                base_url=str(request.url).split("?")[0],
            ),
        )
