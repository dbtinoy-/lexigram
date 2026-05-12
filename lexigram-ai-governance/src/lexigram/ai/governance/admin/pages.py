"""Management pages for the AI governance admin contributor.

Pages are instantiated by the admin runtime from dotted-path handlers;
dependencies are resolved from the DI container.  Every page renders an
explicit unavailable state when a dependency is missing and never
injects unescaped values.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from starlette.responses import HTMLResponse

from lexigram.ai.governance.relay_billing import (
    RelayReservationManager,
    RelayUsageReport,
    RelayUsageReportService,
    RelayUsageTotals,
)
from lexigram.contracts.ai.governance import (
    RelayUsageStoreProtocol,
)
from lexigram.logging import get_logger
from lexigram.primitives import clock
from lexigram.ui import Card, Divider, Grid, StatCard, el, render_to_string

__all__ = [
    "GovernanceQuotasPage",
    "GovernanceRelaySettlementsPage",
    "GovernanceRelayUsagePage",
]

logger = get_logger(__name__)

_DEFAULT_HOURS = 24
_PAGE_SIZE = 20

_TERMINAL_COLORS = {
    "completed": "bg-green-100 text-green-700",
    "failed": "bg-red-100 text-red-700",
    "cancelled": "bg-gray-100 text-gray-500",
    "truncated": "bg-yellow-100 text-yellow-700",
}


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


def _status_badge(status: str) -> Any:
    """Render a status badge for a relay billing status."""
    return el(
        "span",
        status,
        class_=(
            f"inline-block px-2 py-0.5 rounded text-xs font-medium "
            f"{_TERMINAL_COLORS.get(status, 'bg-gray-100 text-gray-500')}"
        ),
    )


def _table(headers: list[str], rows: list[Any]) -> Any:
    """Build a styled table element."""
    return el(
        "table",
        el(
            "thead",
            el(
                "tr",
                *[
                    el(
                        "th",
                        header,
                        class_=(
                            "text-left text-xs font-semibold "
                            "text-[var(--muted-foreground)] uppercase tracking-wider "
                            "pb-1 pr-3"
                        ),
                        scope_="col",
                    )
                    for header in headers
                ],
            ),
        ),
        el("tbody", *rows, class_="divide-y divide-[var(--border)]"),
        class_="w-full",
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
                        class_="text-sm text-[var(--muted-foreground)] py-4",
                    )
                ),
                class_="border-yellow-300 bg-yellow-50",
            ),
        )
    )
    return HTMLResponse(html)


def _report_cards(totals: RelayUsageTotals) -> Grid:
    """Render the aggregate stat cards for one usage report."""
    return Grid(
        StatCard(label="Requests", value=str(totals.request_count), icon="activity"),
        StatCard(
            label="Total Tokens",
            value=f"{totals.total_tokens:,}",
            icon="bar-chart",
        ),
        StatCard(
            label="Prompt / Completion",
            value=f"{totals.prompt_tokens:,} / {totals.completion_tokens:,}",
            icon="cpu",
        ),
        StatCard(
            label="Total Charge",
            value=f"{totals.total_charge:.4f}",
            icon="dollar-sign",
        ),
        cols={"default": 1, "lg": 4},
        gap=4,
    )


def _status_legend(totals: RelayUsageTotals) -> str:
    """Humanize status counts for the report header line."""
    parts = [f"{status} {count}" for status, count in totals.status_counts.items()]
    return " · ".join(parts) if parts else "no requests"


def _usage_rows(report: RelayUsageReport) -> list[Any]:
    """Build table rows for a usage report page."""
    rows: list[Any] = []
    for record in report.rows:
        rows.append(
            el(
                "tr",
                el(
                    "td",
                    record.request_id,
                    class_="py-1.5 pr-3 font-mono text-xs",
                ),
                el("td", record.scope.tenant_id, class_="py-1.5 pr-3"),
                el(
                    "td",
                    record.scope.user_id or "-",
                    class_="py-1.5 pr-3",
                ),
                el("td", record.scope.model or "-", class_="py-1.5 pr-3"),
                el(
                    "td",
                    str(record.usage.total_tokens),
                    class_="py-1.5 pr-3",
                ),
                el(
                    "td",
                    f"{record.charge:.4f}",
                    class_="py-1.5 pr-3",
                ),
                el("td", _status_badge(record.status), class_="py-1.5 pr-3"),
                el(
                    "td",
                    ", ".join(record.loss_codes) or "-",
                    class_="py-1.5",
                ),
            )
        )
    return rows


class GovernanceRelayUsagePage:
    """Management page at /admin/ai-governance/relay-usage."""

    def __init__(self, store: RelayUsageStoreProtocol | None = None) -> None:
        self._reporter = RelayUsageReportService(store) if store is not None else None

    async def handle(self, request: Any) -> HTMLResponse:
        """Render a paginated relay usage report for the window.

        Args:
            request: The starlette request.

        Returns:
            The rendered usage report page HTML.
        """
        page, page_size, hours = _page(request)
        if self._reporter is None:
            return _unavailable_page(
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
            return _unavailable_page("Relay Usage", str(exc))

        totals = report.totals
        header = el(
            "div",
            el(
                "p",
                (
                    f"{start:%Y-%m-%d %H:%M} UTC — {end:%Y-%m-%d %H:%M} UTC "
                    f"(last {hours}h)"
                ),
                class_="text-sm text-[var(--muted-foreground)]",
            ),
            el(
                "p",
                f"{report.total_rows} requests · {_status_legend(totals)}",
                class_="text-sm text-[var(--muted-foreground)] mt-1",
            ),
        )
        rows = _usage_rows(report)
        table = (
            _table(
                [
                    "Request",
                    "Tenant",
                    "User",
                    "Model",
                    "Tokens",
                    "Charge",
                    "Status",
                    "Loss Codes",
                ],
                rows,
            )
            if rows
            else el(
                "p",
                "No relay usage in this window.",
                class_="text-sm text-[var(--muted-foreground)] py-4",
            )
        )
        html = render_to_string(
            el(
                "div",
                el(
                    "h1",
                    "Relay Usage",
                    class_="text-2xl font-bold text-[var(--foreground)]",
                ),
                el(
                    "p",
                    "Settled request usage for the selected UTC window.",
                    class_="text-sm text-[var(--muted-foreground)] mt-1 mb-6",
                ),
                Divider(),
                _report_cards(totals),
                header,
                Card(title="Requests", content=render_to_string(table)),
                el("div", class_="p-6"),
            )
        )
        return HTMLResponse(html)


class GovernanceQuotasPage:
    """Management page at /admin/ai-governance/relay-quotas."""

    def __init__(self, manager: RelayReservationManager | None = None) -> None:
        self._manager = manager

    async def handle(self, request: Any) -> HTMLResponse:
        """Render current quota pressure per configured dimension.

        Args:
            request: The starlette request.

        Returns:
            The rendered quota pressure page HTML.
        """
        del request
        if self._manager is None:
            return _unavailable_page(
                "Relay Quotas",
                "Quota reporting requires the reservation manager.",
            )
        snapshot = await self._manager.quota_snapshot()
        cards: list[Any] = []
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
            cards.append(_quota_card(entry))
        body = (
            Grid(*cards, cols={"default": 1, "lg": 2}, gap=4)
            if cards
            else el(
                "p",
                "No quota limits configured; every dimension is unlimited.",
                class_="text-sm text-[var(--muted-foreground)] py-4",
            )
        )
        html = render_to_string(
            el(
                "div",
                el(
                    "h1",
                    "Relay Quotas",
                    class_="text-2xl font-bold text-[var(--foreground)]",
                ),
                el(
                    "p",
                    "Admission capacity per configured scope dimension.",
                    class_="text-sm text-[var(--muted-foreground)] mt-1 mb-6",
                ),
                Divider(),
                body,
                el("div", class_="p-6"),
            )
        )
        return HTMLResponse(html)


def _quota_card(entry: Any) -> Card:
    """Render one dimension's quota entry as a card."""
    used_tokens = f"{entry.used_tokens:,} / {entry.max_tokens:,}"
    used_charge = f"{entry.used_charge:.4f} / {entry.max_charge:.4f}"
    return Card(
        title=f"{entry.dimension.title()} — {entry.value}",
        content=render_to_string(
            el(
                "div",
                el(
                    "p",
                    used_tokens,
                    class_="text-sm py-1",
                ),
                el(
                    "p",
                    used_charge,
                    class_="text-sm py-1",
                ),
                el(
                    "p",
                    (
                        f"Remaining {entry.remaining_tokens():,} tokens · "
                        f"{entry.remaining_charge():.4f} charge"
                    ),
                    class_="text-sm text-[var(--muted-foreground)] py-1",
                ),
            )
        ),
    )


class GovernanceSettlementsPage:
    """Management page at /admin/ai-governance/relay-settlements."""

    def __init__(self, store: RelayUsageStoreProtocol | None = None) -> None:
        self._reporter = RelayUsageReportService(store) if store is not None else None

    async def handle(self, request: Any) -> HTMLResponse:
        """Render settlement failures as table rows plus counts.

        Args:
            request: The starlette request.

        Returns:
            The rendered settlement view page HTML.
        """
        page, page_size, hours = _page(request)
        if self._reporter is None:
            return _unavailable_page(
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
        totals = report.totals
        count = sum(totals.status_counts.values())
        rows = _usage_rows(report)
        table = (
            _table(
                [
                    "Request",
                    "Tenant",
                    "User",
                    "Model",
                    "Tokens",
                    "Charge",
                    "Status",
                    "Loss Codes",
                ],
                rows,
            )
            if rows
            else el(
                "p",
                "No failed settlements in this window.",
                class_="text-sm text-[var(--muted-foreground)] py-4",
            )
        )
        html = render_to_string(
            el(
                "div",
                el(
                    "h1",
                    "Relay Settlements",
                    class_="text-2xl font-bold text-[var(--foreground)]",
                ),
                el(
                    "p",
                    "Failed settlement records and conversion loss codes.",
                    class_="text-sm text-[var(--muted-foreground)] mt-1 mb-6",
                ),
                Divider(),
                Grid(
                    StatCard(label="Failed", value=str(count), icon="alert-triangle"),
                    StatCard(
                        label="Charge on Failures",
                        value=f"{report.totals.total_charge:.4f}",
                        icon="dollar-sign",
                    ),
                    StatCard(
                        label="Calls", value=str(report.total_rows), icon="activity"
                    ),
                    cols={"default": 1, "lg": 3},
                    gap=4,
                ),
                Card(
                    title=f"Failed Settlements (last {hours}h)",
                    content=render_to_string(table),
                ),
                el("div", class_="p-6"),
            )
        )
        return HTMLResponse(html)
