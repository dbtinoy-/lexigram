"""Tests for the database-backed relay billing store."""

from __future__ import annotations

import asyncio
import sqlite3
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from lexigram.ai.governance.relay_billing import DatabaseRelayUsageStore
from lexigram.contracts.ai.governance import (
    RelayUsageRecord,
    RelayUsageReservation,
    RelayUsageScope,
    RelayUsageStoreProtocol,
)
from lexigram.contracts.ai.relay import RelayUsage
from lexigram.contracts.data import QueryResult, DatabaseProviderProtocol
from lexigram.primitives import clock
from lexigram.testing.clock import FixedClock

START = datetime(2030, 1, 1, 0, 0, 0, tzinfo=UTC)


def clock_override(c: FixedClock):
    """Override the ambient clock within a context block."""
    return clock.use(c)


def make_scope(**overrides: str | None) -> RelayUsageScope:
    """Build a RelayUsageScope with sane defaults."""
    defaults = {
        "tenant_id": "tenant-a",
        "account_id": "acct-1",
        "user_id": "user-1",
        "model": "gpt-4o-mini",
        "provider": "openai",
        "channel": "default",
    }
    defaults.update(overrides)
    return RelayUsageScope(**defaults)


def make_reservation(**overrides: Any) -> RelayUsageReservation:
    """Build a reservation with a future expiry relative to the fixed clock."""
    values = {
        "reservation_id": "res-1",
        "request_id": "req-1",
        "estimated_tokens": 150,
        "estimated_charge": Decimal("1.50"),
        "expires_at": START + timedelta(minutes=5),
    }
    values.update(overrides)
    return RelayUsageReservation(**values)


def make_record(**overrides: Any) -> RelayUsageRecord:
    """Build a settled usage record for one attempt."""
    values = {
        "request_id": "req-1",
        "attempt_id": "res-1",
        "scope": make_scope(),
        "usage": RelayUsage(prompt_tokens=100, completion_tokens=200),
        "charge": Decimal("5.00"),
        "currency": "USD",
        "status": "completed",
        "converter_id": "openai_responses_to_claude",
        "loss_codes": ("tools_adapted",),
    }
    values.update(overrides)
    return RelayUsageRecord(**values)


class SqliteFakeDatabase(DatabaseProviderProtocol):
    """In-memory SQLite fake implementing ``DatabaseProviderProtocol``.

    ``execute`` and ``execute_query`` run against a real in-memory SQLite
    database so unique constraints, ``INSERT OR IGNORE``, and update
    predicates behave exactly as they would in production.
    """

    def __init__(self) -> None:
        self._conn = sqlite3.connect(":memory:")
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")

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

    async def execute(
        self,
        sql: str,
        params: Any = None,
    ) -> QueryResult:
        """Execute a raw statement and commit."""
        return self._result(sql, list(params) if params is not None else None)

    async def execute_query(
        self,
        sql: str,
        params: list[Any] | None = None,
        **kwargs: Any,
    ) -> QueryResult:
        """Execute a read query returning rows."""
        return self._result(sql, params)

    async def table_exists(self, table_name: str) -> bool:
        rows = self._result(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            [table_name],
        )
        return bool(rows.rows)

    async def reservation_status(self, reservation_id: str) -> str | None:
        """Read the stored reservation status for an id."""
        rows = self._result(
            "SELECT status FROM ai_relay_reservations WHERE reservation_id=?",
            [reservation_id],
        )
        if not rows.rows:
            return None
        return rows.rows[0]["status"]


class TestSaveReservation:
    @pytest.mark.asyncio
    async def test_inserts_reservation_row(self) -> None:
        with clock_override(FixedClock(START)):
            db = SqliteFakeDatabase()
            store: RelayUsageStoreProtocol = DatabaseRelayUsageStore(db=db)

            await store.save_reservation(make_reservation())

            assert await db.reservation_status("res-1") == "reserved"

    @pytest.mark.asyncio
    async def test_duplicate_save_is_idempotent(self) -> None:
        with clock_override(FixedClock(START)):
            db = SqliteFakeDatabase()
            store: RelayUsageStoreProtocol = DatabaseRelayUsageStore(db=db)

            await store.save_reservation(make_reservation())
            await store.save_reservation(make_reservation(estimated_tokens=999))

            assert await db.reservation_status("res-1") == "reserved"
            rows = db._conn.execute(
                "SELECT COUNT(*) AS n FROM ai_relay_reservations WHERE reservation_id='res-1'"
            ).fetchone()
            assert rows["n"] == 1


class TestSettleOnce:
    @pytest.mark.asyncio
    async def test_settle_writes_usage_and_marks_reserved_settled(self) -> None:
        with clock_override(FixedClock(START)):
            db = SqliteFakeDatabase()
            store: RelayUsageStoreProtocol = DatabaseRelayUsageStore(db=db)
            reservation = make_reservation()
            await store.save_reservation(reservation)

            stored = await store.settle_once(make_record())

            assert stored.request_id == "req-1"
            assert stored.attempt_id == "res-1"
            assert stored.charge == Decimal("5.00")
            assert stored.usage.prompt_tokens == 100
            assert stored.usage.completion_tokens == 200
            assert stored.loss_codes == ("tools_adapted",)
            assert await db.reservation_status("res-1") == "settled"

    @pytest.mark.asyncio
    async def test_settle_returns_existing_record_and_does_not_double_charge(
        self,
    ) -> None:
        with clock_override(FixedClock(START)):
            db = SqliteFakeDatabase()
            store: RelayUsageStoreProtocol = DatabaseRelayUsageStore(db=db)
            await store.save_reservation(make_reservation())
            first = await store.settle_once(make_record())
            second = await store.settle_once(make_record())

            assert first.attempt_id == second.attempt_id
            assert first.charge == second.charge
            rows = db._conn.execute(
                "SELECT COUNT(*) AS n FROM ai_relay_usage WHERE request_id='req-1'"
            ).fetchone()
            assert rows["n"] == 1

    @pytest.mark.asyncio
    async def test_concurrent_settles_produce_one_record(self) -> None:
        with clock_override(FixedClock(START)):
            db = SqliteFakeDatabase()
            store: RelayUsageStoreProtocol = DatabaseRelayUsageStore(db=db)
            await store.save_reservation(make_reservation())

            first, second = await asyncio.gather(
                store.settle_once(make_record()),
                store.settle_once(make_record()),
            )

            assert first.attempt_id == second.attempt_id
            assert (first.request_id, first.attempt_id) == (
                second.request_id,
                second.attempt_id,
            )
            rows = db._conn.execute(
                "SELECT COUNT(*) AS n FROM ai_relay_usage WHERE request_id='req-1'"
            ).fetchone()
            assert rows["n"] == 1


class TestRelease:
    @pytest.mark.asyncio
    async def test_release_marks_reservation_released(self) -> None:
        with clock_override(FixedClock(START)):
            db = SqliteFakeDatabase()
            store: RelayUsageStoreProtocol = DatabaseRelayUsageStore(db=db)
            await store.save_reservation(make_reservation())

            await store.release("res-1")

            assert await db.reservation_status("res-1") == "released"

    @pytest.mark.asyncio
    async def test_release_after_settle_does_not_revert_state(self) -> None:
        with clock_override(FixedClock(START)):
            db = SqliteFakeDatabase()
            store: RelayUsageStoreProtocol = DatabaseRelayUsageStore(db=db)
            reservation = make_reservation()
            await store.save_reservation(reservation)
            await store.settle_once(make_record())

            await store.release("res-1")

            assert await db.reservation_status("res-1") == "settled"

    @pytest.mark.asyncio
    async def test_release_marks_expired_reservation_expired(self) -> None:
        with clock_override(FixedClock(START)):
            db = SqliteFakeDatabase()
            store: RelayUsageStoreProtocol = DatabaseRelayUsageStore(db=db)
            await store.save_reservation(
                make_reservation(expires_at=START - timedelta(seconds=1))
            )

            with clock_override(FixedClock(START)):
                await store.release("res-1")

            assert await db.reservation_status("res-1") == "expired"

    @pytest.mark.asyncio
    async def test_release_unknown_id_is_harmless(self) -> None:
        with clock_override(FixedClock(START)):
            db = SqliteFakeDatabase()
            store: RelayUsageStoreProtocol = DatabaseRelayUsageStore(db=db)

            await store.release("nope")

            assert True


class TestQuery:
    @pytest.mark.asyncio
    async def test_query_filters_by_scope(self) -> None:
        with clock_override(FixedClock(START)):
            db = SqliteFakeDatabase()
            store: RelayUsageStoreProtocol = DatabaseRelayUsageStore(db=db)
            await store.save_reservation(make_reservation())
            await store.settle_once(make_record())

            results = await store.query({"tenant_id": "tenant-a"})
            assert len(results) == 1
            assert results[0].request_id == "req-1"

            results = await store.query({"tenant_id": "tenant-zzz"})
            assert len(results) == 0

    @pytest.mark.asyncio
    async def test_query_by_status_filters(self) -> None:
        with clock_override(FixedClock(START)):
            db = SqliteFakeDatabase()
            store: RelayUsageStoreProtocol = DatabaseRelayUsageStore(db=db)
            await store.save_reservation(make_reservation())
            await store.settle_once(make_record())

            results = await store.query({"status": "completed"})
            assert len(results) == 1

            results = await store.query({"status": "failed"})
            assert len(results) == 0

    @pytest.mark.asyncio
    async def test_round_trip_preserves_usage_and_metadata(self) -> None:
        with clock_override(FixedClock(START)):
            db = SqliteFakeDatabase()
            store: RelayUsageStoreProtocol = DatabaseRelayUsageStore(db=db)
            await store.save_reservation(make_reservation())
            lossy = RelayUsage(
                prompt_tokens=10,
                completion_tokens=20,
                cache_read_tokens=30,
                cache_creation_tokens=40,
                reasoning_tokens=50,
                audio_input_tokens=60,
                audio_output_tokens=70,
                image_tokens=80,
                input_tokens=90,
                output_tokens=100,
                total_tokens_override=110,
            )
            await store.settle_once(
                make_record(
                    usage=lossy,
                    currency="EUR",
                    status="cancelled",
                    loss_codes=("a", "b"),
                )
            )

            (stored,) = await store.query({"request_id": "req-1"})

            assert stored.usage == lossy
            assert stored.currency == "EUR"
            assert stored.status == "cancelled"
            assert stored.loss_codes == ("a", "b")