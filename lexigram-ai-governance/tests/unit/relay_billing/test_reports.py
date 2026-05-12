"""Tests for the relay usage report service and quota snapshots.

Covers scope filters, UTC time windows, terminal statuses, token totals,
Decimal charge aggregation, loss-code and status counts, pagination,
reserved-versus-released quota, remaining quota, and bounded-input
rejection.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Literal

import pytest

from lexigram.ai.governance.relay_billing import (
    RelayQuotaSnapshot,
    RelayReservationLimits,
    RelayReservationManager,
    RelayScopeLimit,
    RelayUsageReportService,
    RelayUsageTotals,
)
from lexigram.contracts.ai.governance import (
    RelayUsageRecord,
    RelayUsageScope,
    RelayUsageStoreProtocol,
)
from lexigram.contracts.ai.relay import JsonValue, RelayUsage

START = datetime(2030, 3, 1, 0, 0, 0, tzinfo=UTC)
WINDOW = timedelta(hours=6)

SCOPE_DEFAULTS = {
    "tenant_id": "tenant-a",
    "account_id": "acct-1",
    "user_id": "user-1",
    "model": "gpt-4o-mini",
    "provider": "openai",
    "channel": "default",
}

TERMINAL_STATUS = Literal["completed", "failed", "cancelled", "truncated"]


def make_scope(**overrides: str) -> RelayUsageScope:
    """Build a usage scope with sane defaults."""
    scope = dict(SCOPE_DEFAULTS)
    scope.update(overrides)
    return RelayUsageScope(**scope)


def make_record(
    request_id: str,
    *,
    scope: RelayUsageScope | None = None,
    status: TERMINAL_STATUS = "completed",
    charge: str = "1.00",
    tokens: int = 100,
    loss_codes: tuple[str, ...] = (),
    currency: str = "USD",
) -> RelayUsageRecord:
    """Build a settled usage record for report tests."""
    return RelayUsageRecord(
        request_id=request_id,
        attempt_id=f"{request_id}-a1",
        scope=scope or make_scope(),
        usage=RelayUsage(prompt_tokens=tokens, completion_tokens=tokens),
        charge=Decimal(charge),
        currency=currency,
        status=status,
        converter_id="relay-converter",
        loss_codes=loss_codes,
    )


def at(minutes: int) -> datetime:
    """Return a timestamp at *minutes* past the window start."""
    return START + timedelta(minutes=minutes)


class FakeUsageStore(RelayUsageStoreProtocol):
    """In-memory store honouring scope and created-window filters."""

    def __init__(self) -> None:
        self._rows: list[tuple[datetime, RelayUsageRecord]] = []

    def add(self, record: RelayUsageRecord, created_at: datetime) -> None:
        """Insert a settled record with a created timestamp."""
        self._rows.append((created_at, record))

    async def save_reservation(self, reservation: object) -> None:
        """No-op reservation persistence."""

    async def settle_once(self, record: RelayUsageRecord) -> RelayUsageRecord:
        """Insert and return the record."""
        self.add(record, datetime.now(UTC))
        return record

    async def release(self, reservation_id: str) -> None:
        """No-op reservation release."""

    async def query(
        self, filters: Mapping[str, JsonValue]
    ) -> Sequence[RelayUsageRecord]:
        """Return rows matching the scope and created-window filters."""
        gte = filters.get("created_at_gte")
        lte = filters.get("created_at_lte")
        status = filters.get("status")
        rows = [
            record
            for created_at, record in self._rows
            if (
                gte is None
                or created_at >= datetime.fromisoformat(str(gte))
            )
            and (
                lte is None
                or created_at <= datetime.fromisoformat(str(lte))
            )
            and (status is None or record.status == status)
            and all(
                filters.get(key) is None or getattr(record.scope, key) == filters[key]
                for key in (
                    "tenant_id",
                    "account_id",
                    "user_id",
                    "model",
                    "provider",
                    "channel",
                )
            )
        ]
        return sorted(rows, key=lambda record: record.request_id)


def make_service(store: FakeUsageStore | None = None) -> RelayUsageReportService:
    """Return a report service over the given store (empty by default)."""
    return RelayUsageReportService(store or FakeUsageStore())


def build_store(
    rows: Sequence[tuple[datetime, RelayUsageRecord]],
) -> FakeUsageStore:
    """Return a store pre-populated with the given rows."""
    store = FakeUsageStore()
    for created_at, record in rows:
        store.add(record, created_at)
    return store


def row_range(
    *request_ids: str, **overrides: object
) -> list[tuple[datetime, RelayUsageRecord]]:
    """Return one default record pair per request ID inside the window."""
    return [
        (at(30 + i), make_record(rid, **overrides))
        for i, rid in enumerate(request_ids)
    ]


class TestWindowValidation:
    """Unbounded or inverted windows are rejected."""

    async def test_missing_start_rejected(self) -> None:
        """A missing window start is rejected."""
        service = make_service()
        with pytest.raises(ValueError, match="window"):
            await service.report(start=None, end=START + WINDOW)

    async def test_missing_end_rejected(self) -> None:
        """A missing window end is rejected."""
        service = make_service()
        with pytest.raises(ValueError, match="window"):
            await service.report(start=START, end=None)

    async def test_both_missing_rejected(self) -> None:
        """Fully unbounded windows are rejected."""
        service = make_service()
        with pytest.raises(ValueError, match="window"):
            await service.report(start=None, end=None)

    async def test_inverted_window_rejected(self) -> None:
        """A window that ends before it starts is rejected."""
        service = make_service()
        with pytest.raises(ValueError, match="end must be after"):
            await service.report(start=START, end=START - timedelta(seconds=1))

    async def test_equal_bounds_rejected(self) -> None:
        """An empty window (start == end) is rejected."""
        service = make_service()
        with pytest.raises(ValueError, match="end must be after"):
            await service.report(start=START, end=START)


class TestPageValidation:
    """Page numbers and page sizes are bounded."""

    async def test_page_size_above_capacity_rejected(self) -> None:
        """A page size above the configured maximum is rejected."""
        service = RelayUsageReportService(FakeUsageStore(), max_page_size=25)
        with pytest.raises(ValueError, match="page_size"):
            await service.report(start=START, end=START + WINDOW, page_size=26)

    async def test_zero_page_size_rejected(self) -> None:
        """A zero page size is rejected."""
        service = make_service()
        with pytest.raises(ValueError, match="page_size"):
            await service.report(start=START, end=START + WINDOW, page_size=0)

    async def test_zero_page_rejected(self) -> None:
        """A zero page number is rejected."""
        service = make_service()
        with pytest.raises(ValueError, match="page"):
            await service.report(start=START, end=START + WINDOW, page=0)

    async def test_unknown_status_rejected(self) -> None:
        """A status outside the terminal set is rejected."""
        service = make_service()
        with pytest.raises(ValueError, match="status"):
            await service.report(start=START, end=START + WINDOW, status="draft")


class TestWindowFiltering:
    """Only records inside the window are counted."""

    async def test_excludes_outside_window(self) -> None:
        """Records before the start and after the end are excluded."""
        store = build_store(
            [
                (START - timedelta(minutes=5), make_record("old")),
                (at(30), make_record("inside")),
                (START + WINDOW + timedelta(minutes=5), make_record("future")),
            ]
        )
        report = await make_service(store).report(start=START, end=START + WINDOW)
        assert [row.request_id for row in report.rows] == ["inside"]
        assert report.total_rows == 1

    async def test_includes_window_edge_records(self) -> None:
        """Records on the window edges are included."""
        store = build_store(
            [
                (START, make_record("at-start")),
                (START + WINDOW, make_record("at-end")),
            ]
        )
        report = await make_service(store).report(start=START, end=START + WINDOW)
        assert report.total_rows == 2

    async def test_utc_window_partitions(self) -> None:
        """UTC day boundaries partition records correctly."""
        midnight = datetime(2030, 3, 5, 0, 0, 0, tzinfo=UTC)
        store = build_store(
            [
                (midnight - timedelta(seconds=1), make_record("prev-day")),
                (midnight, make_record("day-start")),
                (midnight + timedelta(hours=23), make_record("day-end")),
            ]
        )
        report = await make_service(store).report(
            start=midnight, end=midnight + timedelta(days=1)
        )
        assert {row.request_id for row in report.rows} == {"day-start", "day-end"}


class TestScopeFilters:
    """Scope filters narrow the aggregation."""

    async def test_tenant_filter(self) -> None:
        """Only the requested tenant is aggregated."""
        store = build_store(
            [
                *row_range("a"),
                (at(60), make_record("b", scope=make_scope(tenant_id="tenant-b"))),
            ]
        )
        report = await make_service(store).report(
            start=START, end=START + WINDOW, tenant_id="tenant-a"
        )
        assert [row.request_id for row in report.rows] == ["a"]
        assert report.totals.request_count == 1

    async def test_channel_filter(self) -> None:
        """Only the requested channel is aggregated."""
        store = build_store(
            [
                (at(30), make_record("c", scope=make_scope(channel="claude"))),
                (at(60), make_record("g", scope=make_scope(channel="gemini"))),
            ]
        )
        report = await make_service(store).report(
            start=START, end=START + WINDOW, channel="gemini"
        )
        assert [row.request_id for row in report.rows] == ["g"]

    async def test_across_dimension_filters(self) -> None:
        """Account, user, model, and provider filters each narrow the set."""
        store = build_store(
            [
                *row_range("match"),
                (at(60), make_record("other-acct", scope=make_scope(account_id="acct-2"))),
                (at(60), make_record("other-user", scope=make_scope(user_id="user-2"))),
                (at(60), make_record("other-model", scope=make_scope(model="claude-sonnet"))),
                (at(60), make_record("other-provider", scope=make_scope(provider="anthropic"))),
            ]
        )
        expectations = {
            "account_id": ["match", "other-model", "other-provider", "other-user"],
            "user_id": ["match", "other-acct", "other-model", "other-provider"],
            "model": ["match", "other-acct", "other-provider", "other-user"],
            "provider": ["match", "other-acct", "other-model", "other-user"],
        }
        for key, expected in expectations.items():
            report = await make_service(store).report(
                start=START, end=START + WINDOW, **{key: SCOPE_DEFAULTS[key]}
            )
            assert [row.request_id for row in report.rows] == expected, key


class TestStatusAggregation:
    """Terminal-status counts are aggregated and filterable."""

    async def test_status_counts(self) -> None:
        """Completed, failed, cancelled, and truncated counts."""
        store = build_store(
            [
                *row_range("c1", "c2"),
                *row_range("f1", status="failed"),
                *row_range("x1", status="cancelled"),
                *row_range("t1", status="truncated"),
            ]
        )
        report = await make_service(store).report(start=START, end=START + WINDOW)
        assert report.totals.status_counts == {
            "completed": 2,
            "failed": 1,
            "cancelled": 1,
            "truncated": 1,
        }

    async def test_status_filter(self) -> None:
        """Only the requested status is aggregated."""
        store = build_store([*row_range("com"), *row_range("f1", status="failed")])
        report = await make_service(store).report(
            start=START, end=START + WINDOW, status="failed"
        )
        assert [row.request_id for row in report.rows] == ["f1"]


class TestTotals:
    """Token and charge totals aggregate across the result set."""

    async def test_token_totals(self) -> None:
        """Prompt/completion and derived total tokens are summed."""
        store = build_store([*row_range("r1", tokens=10), *row_range("r2", tokens=20)])
        report = await make_service(store).report(start=START, end=START + WINDOW)
        assert report.totals.prompt_tokens == 30
        assert report.totals.completion_tokens == 30
        assert report.totals.total_tokens == 60

    async def test_charge_total_is_decimal(self) -> None:
        """Charge accumulates with Decimal arithmetic, not floats."""
        store = build_store(
            [*row_range("r1", charge="0.10"), *row_range("r2", charge="0.20")]
        )
        report = await make_service(store).report(start=START, end=START + WINDOW)
        assert isinstance(report.totals.total_charge, Decimal)
        assert report.totals.total_charge == Decimal("0.30")

    async def test_empty_result_totals_zero(self) -> None:
        """An empty result set reports zero rows and zero charge."""
        report = await make_service().report(start=START, end=START + WINDOW)
        assert report.total_rows == 0
        assert report.totals.request_count == 0
        assert report.totals.total_charge == Decimal("0")
        assert isinstance(report.totals.total_charge, Decimal)
        assert not report.totals.status_counts


class TestPagination:
    """Pagination slices the full result set deterministically."""

    async def test_first_page(self) -> None:
        """The first page returns the leading slice."""
        store = build_store(row_range(*(f"r{i}" for i in range(5))))
        report = await make_service(store).report(
            start=START, end=START + WINDOW, page=1, page_size=2
        )
        assert [row.request_id for row in report.rows] == ["r0", "r1"]
        assert report.total_rows == 5

    async def test_second_page(self) -> None:
        """The second page returns the next slice."""
        store = build_store(row_range(*(f"r{i}" for i in range(5))))
        report = await make_service(store).report(
            start=START, end=START + WINDOW, page=2, page_size=2
        )
        assert [row.request_id for row in report.rows] == ["r2", "r3"]
        assert report.total_rows == 5

    async def test_page_beyond_end_is_empty(self) -> None:
        """A page past the end of the set returns no rows."""
        store = build_store(row_range("only"))
        report = await make_service(store).report(
            start=START, end=START + WINDOW, page=10, page_size=2
        )
        assert report.rows == ()
        assert report.total_rows == 1

    async def test_totals_cover_full_set_not_page(self) -> None:
        """Totals aggregate every matched row, not just the current page."""
        store = build_store(row_range(*(f"r{i}" for i in range(5))))
        report = await make_service(store).report(
            start=START, end=START + WINDOW, page=1, page_size=2
        )
        assert report.totals.request_count == 5


class TestLossCodePreservation:
    """Loss codes are counted, not dropped."""

    async def test_loss_counts_preserved(self) -> None:
        """Loss codes aggregate into per-code totals."""
        store = build_store(
            [
                *row_range("r1", loss_codes=("model_not_found",)),
                *row_range("r2", loss_codes=("model_not_found", "prompt_too_long")),
            ]
        )
        report = await make_service(store).report(start=START, end=START + WINDOW)
        assert report.totals.loss_counts == {
            "model_not_found": 2,
            "prompt_too_long": 1,
        }


class TestQuotaSnapshot:
    """Reserved versus remaining quota is reportable from the manager."""

    def _manager_with_tenant_limit(
        self,
    ) -> tuple[RelayReservationManager, RelayReservationLimits]:
        limits = RelayReservationLimits(
            tenant=RelayScopeLimit(max_tokens=1_000, max_charge=Decimal("10")),
        )
        return RelayReservationManager(limits), limits

    async def test_quota_snapshot_reports_limits_and_usage(self) -> None:
        """Configured limits appear with current usage after a reserve."""
        manager, _ = self._manager_with_tenant_limit()
        outcome = await manager.reserve(
            "req-1", make_scope(), 400, Decimal("2.00")
        )
        assert outcome.is_ok()
        snapshot = await manager.quota_snapshot()
        assert snapshot.tenant is not None
        assert snapshot.tenant.value == "tenant-a"
        assert snapshot.tenant.max_tokens == 1_000
        assert snapshot.tenant.max_charge == Decimal("10")
        assert snapshot.tenant.used_tokens == 400
        assert snapshot.tenant.used_charge == Decimal("2.00")

    async def test_unlimited_dimensions_absent_from_snapshot(self) -> None:
        """Dimensions without a configured limit never appear."""
        manager = RelayReservationManager()
        snapshot = await manager.quota_snapshot()
        assert snapshot.tenant is None
        assert snapshot.channel is None
        assert isinstance(snapshot, RelayQuotaSnapshot)

    async def test_used_and_remaining_after_reserve(self) -> None:
        """Reserved amounts count toward usage; remaining is exposed."""
        manager, _ = self._manager_with_tenant_limit()
        await manager.reserve("req-1", make_scope(), 400, Decimal("3.00"))
        snapshot = await manager.quota_snapshot()
        assert snapshot.tenant is not None
        assert snapshot.tenant.used_tokens == 400
        assert snapshot.tenant.used_charge == Decimal("3.00")
        assert snapshot.tenant.remaining_tokens() == 600
        assert snapshot.tenant.remaining_charge() == Decimal("7.00")

    async def test_release_frees_reserved_quota(self) -> None:
        """Releasing a reservation frees the reported quota again."""
        manager, _ = self._manager_with_tenant_limit()
        outcome = await manager.reserve("req-1", make_scope(), 800, Decimal("9.00"))
        assert outcome.is_ok()
        reservation = outcome.unwrap()
        blocked = await manager.reserve("req-2", make_scope(), 300, Decimal("1.00"))
        assert blocked.is_err()
        await manager.release(reservation.reservation_id)
        second = await manager.reserve("req-2", make_scope(), 300, Decimal("1.00"))
        assert second.is_ok()
        snapshot = await manager.quota_snapshot()
        assert snapshot.tenant is not None
        assert snapshot.tenant.used_charge == Decimal("1.00")
        assert snapshot.tenant.remaining_tokens() == 700