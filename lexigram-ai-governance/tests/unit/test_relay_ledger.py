"""Tests for the governance relay ledger service and store."""

from __future__ import annotations

import sqlite3
from typing import Any

import pytest

from lexigram.ai.governance.relay_ledger import (
    RelayLedgerService,
    SqlRelayLedgerStore,
)
from lexigram.contracts.ai.governance import RelayUsageScope
from lexigram.contracts.ai.relay import (
    RelayCheckinRecord,
    RelayLedgerServiceProtocol,
    RelayTopUpRecord,
)
from lexigram.contracts.data import DatabaseProviderProtocol, QueryResult
from lexigram.result import Err, Ok


class SqliteFakeDatabase(DatabaseProviderProtocol):
    """In-memory SQLite fake implementing ``DatabaseProviderProtocol``."""

    def __init__(self) -> None:
        self._conn = sqlite3.connect(":memory:")
        self._conn.row_factory = sqlite3.Row

    def _result(self, sql: str, params: list[Any] | None = None) -> QueryResult:
        cur = self._conn.execute(sql, params or [])
        rows = list(cur)
        self._conn.commit()
        return QueryResult(
            rows=[dict(row) for row in rows],
            row_count=cur.rowcount,
            execution_time=0.0,
            success=True,
        )

    async def execute(self, sql: str, params: Any = None) -> QueryResult:
        return self._result(sql, list(params) if params is not None else None)

    async def execute_query(
        self, sql: str, params: list[Any] | None = None, **kwargs: Any
    ) -> QueryResult:
        return self._result(sql, params)


@pytest.fixture
def database() -> SqliteFakeDatabase:
    return SqliteFakeDatabase()


@pytest.fixture
def service(database: SqliteFakeDatabase) -> RelayLedgerService:
    store = SqlRelayLedgerStore(database)
    return RelayLedgerService(store=store)


async def _rows(database: SqliteFakeDatabase, sql: str) -> list[dict[str, Any]]:
    result = await database.execute_query(sql)
    return result.rows


class TestCredit:
    async def test_credit_journals_completed_topup(
        self, service: RelayLedgerService, database: SqliteFakeDatabase
    ) -> None:
        scope = RelayUsageScope(tenant_id="t1", user_id="u1")
        result = await service.credit(scope, "100", "manual adjustment")
        assert isinstance(result, Ok)
        rows = await _rows(database, "SELECT * FROM ai_relay_topups")
        assert len(rows) == 1
        assert rows[0]["user_id"] == "u1"
        assert rows[0]["amount"] == "100"
        assert rows[0]["status"] == "completed"
        assert rows[0]["created_at"]

    async def test_credit_rejects_negative_amount(
        self, service: RelayLedgerService, database: SqliteFakeDatabase
    ) -> None:
        scope = RelayUsageScope(tenant_id="t1", user_id="u1")
        result = await service.credit(scope, "-5", "bad")
        assert isinstance(result, Err)
        assert result.unwrap_err().code == "invalid_amount"

    async def test_credit_requires_user_scope(
        self, service: RelayLedgerService, database: SqliteFakeDatabase
    ) -> None:
        scope = RelayUsageScope(tenant_id="t1")
        result = await service.credit(scope, "10", "no user")
        assert isinstance(result, Err)


class TestSettleTopup:
    async def test_settle_flips_pending_to_completed_once(
        self, service: RelayLedgerService, database: SqliteFakeDatabase
    ) -> None:
        await _seed_pending(database, "ref-1", "u1", "50")
        first = await service.settle_topup("ref-1", "pending")
        assert isinstance(first, Ok)
        second = await service.settle_topup("ref-1", "pending")
        assert isinstance(second, Err)
        assert second.unwrap_err().code == "stale_settlement"
        rows = await _rows(
            database, "SELECT status FROM ai_relay_topups WHERE reference_id='ref-1'"
        )
        assert rows[0]["status"] == "completed"

    async def test_settle_unknown_reference_fails(
        self, service: RelayLedgerService, database: SqliteFakeDatabase
    ) -> None:
        result = await service.settle_topup("ghost", "pending")
        assert isinstance(result, Err)
        assert result.unwrap_err().code == "not_found"


class TestCheckin:
    async def test_checkin_awards_once_per_day(
        self, service: RelayLedgerService, database: SqliteFakeDatabase
    ) -> None:
        first = await service.checkin("u1", "25")
        assert isinstance(first, Ok)
        record = first.unwrap()
        assert isinstance(record, RelayCheckinRecord)
        assert record.user_id == "u1"
        assert record.award == "25"
        second = await service.checkin("u1", "25")
        assert isinstance(second, Err)
        assert second.unwrap_err().code == "already_checked_in"
        rows = await _rows(database, "SELECT * FROM ai_relay_checkins")
        assert len(rows) == 1

    async def test_checkin_awards_caller_supplied_amount(
        self, service: RelayLedgerService, database: SqliteFakeDatabase
    ) -> None:
        result = await service.checkin("u1", "5")
        assert isinstance(result, Ok)
        assert result.unwrap().award == "5"

    async def test_checkin_rejects_negative_award(
        self, service: RelayLedgerService, database: SqliteFakeDatabase
    ) -> None:
        result = await service.checkin("u1", "-1")
        assert isinstance(result, Err)
        assert result.unwrap_err().code == "invalid_amount"


class TestListTopups:
    async def test_list_filters_user_and_orders_newest_first(
        self, service: RelayLedgerService, database: SqliteFakeDatabase
    ) -> None:
        await _seed_pending(database, "ref-1", "u1", "10")
        await _seed_pending(database, "ref-2", "u1", "20")
        await _seed_pending(database, "ref-3", "u2", "30")
        rows = await service.list_topups("u1", 10)
        assert isinstance(rows, list)
        assert all(isinstance(row, RelayTopUpRecord) for row in rows)
        assert [row.reference_id for row in rows] == ["ref-2", "ref-1"]
        only_u2 = await service.list_topups("u2", 10)
        assert [row.reference_id for row in only_u2] == ["ref-3"]

    async def test_list_limits_results(
        self, service: RelayLedgerService, database: SqliteFakeDatabase
    ) -> None:
        await _seed_pending(database, "ref-1", "u1", "10")
        await _seed_pending(database, "ref-2", "u1", "20")
        rows = await service.list_topups("u1", 1)
        assert [row.reference_id for row in rows] == ["ref-2"]


class TestProtocol:
    async def test_service_implements_protocol(
        self, service: RelayLedgerService
    ) -> None:
        assert isinstance(service, RelayLedgerServiceProtocol)


async def _seed_pending(
    database: SqliteFakeDatabase, reference_id: str, user_id: str, amount: str
) -> None:
    store = SqlRelayLedgerStore(database)
    await store.insert_topup(
        RelayTopUpRecord(
            reference_id=reference_id,
            user_id=user_id,
            amount=amount,
            status="pending",
            created_at="2026-08-10T00:00:00+00:00",
        )
    )
