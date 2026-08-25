"""Renderers for AI governance dashboard widgets.

Each renderer receives its resolved dependencies explicitly (the usage
report service and/or the reservation manager) and returns widget
content.  A ``None`` dependency renders an explicit unavailable state —
never zero usage or quota as if it were measured.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from lexigram.ai.governance.relay_billing import (
    RelayUsageReport,
    RelayUsageReportService,
)
from lexigram.contracts.admin.types import WidgetParams
from lexigram.contracts.admin.widget_content import (
    MessageContent,
    Stat,
    StatContent,
    WidgetContent,
)
from lexigram.primitives import clock

if TYPE_CHECKING:
    from lexigram.ai.governance.relay_billing import RelayReservationManager

__all__ = [
    "render_current_spend",
    "render_quota_pressure",
    "render_settlement_failures",
    "render_token_dimensions",
]


async def _report_window(
    reporter: RelayUsageReportService,
    minutes: int,
    *,
    status: str | None = None,
) -> RelayUsageReport:
    """Run a windowed report for widget data.

    Args:
        reporter: The report service to query.
        minutes: Widget window length in minutes.
        status: Optional terminal status filter.

    Returns:
        The bounded usage report for the window.
    """
    end = clock.now()
    start = end - timedelta(minutes=minutes)
    return await reporter.report(
        start=start,
        end=end,
        page=1,
        page_size=1,
        status=status,
    )


async def render_current_spend(
    reporter: RelayUsageReportService | None,
    params: WidgetParams,
) -> WidgetContent:
    """Render the settled charge for the widget window."""
    if reporter is None:
        return MessageContent(text="Billing store unavailable; spend not measured.")
    report = await _report_window(reporter, params.time_window_minutes)
    return StatContent(
        stats=(
            Stat(label="Current Spend", value=f"{report.totals.total_charge:.4f}"),
            Stat(
                label="Request Volume",
                value=f"{report.total_rows} requests in the window",
            ),
        )
    )


async def render_token_dimensions(
    reporter: RelayUsageReportService | None,
    params: WidgetParams,
) -> WidgetContent:
    """Render prompt/completion/total tokens for the window."""
    if reporter is None:
        return MessageContent(text="Billing reporting unavailable; no token data.")
    report = await _report_window(reporter, params.time_window_minutes)
    totals = report.totals
    return StatContent(
        stats=(
            Stat(label="Prompt Tokens", value=f"{totals.prompt_tokens:,}"),
            Stat(label="Completion Tokens", value=f"{totals.completion_tokens:,}"),
            Stat(label="Total Tokens", value=f"{totals.total_tokens:,}"),
        )
    )


async def render_quota_pressure(
    manager: RelayReservationManager | None,
) -> WidgetContent:
    """Render remaining capacity per configured dimension."""
    if manager is None:
        return MessageContent(
            text="Quota reporting unavailable; reservation manager missing."
        )
    snapshot = await manager.quota_snapshot()
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
                label=f"{entry.dimension}",
                value=(
                    f"{entry.remaining_tokens():,} tokens · "
                    f"{entry.remaining_charge():.4f} charge"
                ),
            )
        )
    if not stats:
        return MessageContent(text="No quota limits configured.")
    return StatContent(stats=tuple(stats))


async def render_settlement_failures(
    reporter: RelayUsageReportService | None,
    params: WidgetParams,
) -> WidgetContent:
    """Render failed settlement counts in the widget window."""
    if reporter is None:
        return MessageContent(text="Billing reporting unavailable; no failure data.")
    report = await _report_window(reporter, params.time_window_minutes, status="failed")
    failed = sum(report.totals.status_counts.values())
    return StatContent(
        stats=(
            Stat(label="Failed Settlements", value=str(failed)),
            Stat(
                label="Failed Charge",
                value=f"{report.totals.total_charge:.4f} charge on failed settlements",
            ),
        )
    )
