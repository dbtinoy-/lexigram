"""Usage and quota reporting for relay billing.

``RelayUsageReportService`` runs bounded, read-only aggregations over
:class:`~lexigram.contracts.ai.governance.RelayUsageStoreProtocol`:
scope and status filters narrow the window, token and charge totals are
computed with integer/Decimal arithmetic, and loss/status counts survive
aggregation.  Reports are always bounded — a window start/end and a
maximum page size are enforced before any store access.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from lexigram.contracts.ai.governance import (
    RelayUsageRecord,
    RelayUsageStoreProtocol,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from lexigram.contracts.ai.relay import JsonValue

__all__ = [
    "TERMINAL_STATUSES",
    "RelayUsageReport",
    "RelayUsageReportService",
    "RelayUsageTotals",
]

TERMINAL_STATUSES = ("completed", "failed", "cancelled", "truncated")


@dataclass(frozen=True, slots=True)
class RelayUsageTotals:
    """Aggregated token, charge, and count totals for a report window.

    Attributes:
        prompt_tokens: Sum of prompt tokens across matched records.
        completion_tokens: Sum of completion tokens across matched records.
        total_tokens: Sum of normalized total tokens.
        total_charge: Sum of charges as exact ``Decimal`` arithmetic.
        request_count: Number of matched records.
        status_counts: Per-terminal-status record counts (non-zero only).
        loss_counts: Per-loss-code occurrence counts (non-zero only).
    """

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    total_charge: Decimal = Decimal("0")
    request_count: int = 0
    status_counts: dict[str, int] = field(default_factory=dict)
    loss_counts: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RelayUsageReport:
    """One page of a usage report plus window totals.

    Attributes:
        rows: The requested page of matched records (empty past the end).
        total_rows: Number of records matching the filters in the window.
        totals: Aggregation across every matched record, not just the page.
    """

    rows: tuple[RelayUsageRecord, ...] = ()
    total_rows: int = 0
    totals: RelayUsageTotals = field(default_factory=RelayUsageTotals)


def _aggregate(records: Sequence[RelayUsageRecord]) -> RelayUsageTotals:
    """Aggregate token/charge/count totals across *records*.

    Args:
        records: The full matched set within the report window.

    Returns:
        Totals with zero entries omitted from the count maps.
    """
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    total_charge = Decimal("0")
    status_counts: dict[str, int] = {}
    loss_counts: dict[str, int] = {}
    for record in records:
        prompt_tokens += record.usage.prompt_tokens
        completion_tokens += record.usage.completion_tokens
        total_tokens += record.usage.total_tokens
        total_charge += record.charge
        status_counts[record.status] = status_counts.get(record.status, 0) + 1
        for code in record.loss_codes:
            loss_counts[code] = loss_counts.get(code, 0) + 1
    return RelayUsageTotals(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        total_charge=total_charge,
        request_count=len(records),
        status_counts=status_counts,
        loss_counts=loss_counts,
    )


class RelayUsageReportService:
    """Read-only aggregation over settled relay usage records.

    Args:
        store: The usage store to query (resolved from the DI container).
        max_page_size: Largest page size accepted by :meth:`report`.
    """

    def __init__(
        self,
        store: RelayUsageStoreProtocol,
        *,
        max_page_size: int = 25,
    ) -> None:
        self._store = store
        self._max_page_size = max_page_size

    async def report(
        self,
        *,
        start: datetime,
        end: datetime,
        page: int = 1,
        page_size: int = 25,
        tenant_id: str | None = None,
        account_id: str | None = None,
        user_id: str | None = None,
        model: str | None = None,
        provider: str | None = None,
        channel: str | None = None,
        status: str | None = None,
    ) -> RelayUsageReport:
        """Run a bounded usage report over a UTC window.

        Args:
            start: Window start (inclusive).
            end: Window end (inclusive).
            page: One-based page number.
            page_size: Number of rows per page, capped by the maximum.
            tenant_id: Narrow the report to one tenant.
            account_id: Narrow the report to one account.
            user_id: Narrow the report to one user.
            model: Narrow the report to one model alias.
            provider: Narrow the report to one provider.
            channel: Narrow the report to one channel.
            status: Narrow the report to one terminal status.

        Returns:
            The requested page plus totals covering the whole window.

        Raises:
            ValueError: For unbounded/inverted windows, non-positive
                pages or page sizes, page sizes above the configured
                maximum, or unknown statuses.
        """
        if start is None or end is None:
            raise ValueError("report requires both start and end window bounds")
        if end <= start:
            raise ValueError("end must be after start")
        if page < 1:
            raise ValueError("page must be at least 1")
        if page_size < 1:
            raise ValueError("page_size must be at least 1")
        if page_size > self._max_page_size:
            raise ValueError(
                f"page_size must not exceed the maximum {self._max_page_size}"
            )
        if status is not None and status not in TERMINAL_STATUSES:
            raise ValueError(
                f"unknown status {status!r}; expected one of {TERMINAL_STATUSES}"
            )

        filters: dict[str, JsonValue] = {
            "created_at_gte": start.isoformat(),
            "created_at_lte": end.isoformat(),
        }
        filters.update(
            {
                key: value
                for key, value in (
                    ("tenant_id", tenant_id),
                    ("account_id", account_id),
                    ("user_id", user_id),
                    ("model", model),
                    ("provider", provider),
                    ("channel", channel),
                )
                if value is not None
            }
        )
        if status is not None:
            filters["status"] = status

        records = await self._store.query(filters)
        offset = (page - 1) * page_size
        return RelayUsageReport(
            rows=tuple(records[offset : offset + page_size]),
            total_rows=len(records),
            totals=_aggregate(records),
        )
