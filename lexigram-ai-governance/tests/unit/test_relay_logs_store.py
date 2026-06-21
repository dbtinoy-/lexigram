"""Tests for the governance relay request-log store and usage service."""

from __future__ import annotations

from datetime import datetime, timezone
import sqlite3
from typing import Any

from lexigram.ai.governance.relay_logs import (
    RelayUsageService,
    SqlRelayRequestLogStore,
)
from lexigram.contracts.ai.relay import (
    RelayDailyUsage,
    RelayModelRank,
    RelayRequestLogEntry,
    RelayRequestLogStoreProtocol,
    RelayUsageServiceProtocol,
)
from lexigram.contracts.data import DatabaseProviderProtocol, QueryResult
from lexigram.primitives import clock
from lexigram.testing.clock import FixedClock


def make_entry(**overrides: Any) -> RelayRequestLogEntry:
    """Build a request-log entry for one dispatch."""
    values: dict[str, Any] = {
        "request_id": "req-1",
        "user_id": "u1",
        "token_id": "t1",
        "endpoint_kind": "chat",
        "model": "gpt-4",
        "channel_name": "ch-1",
        "status": "completed",
        "created_at": datetime(2026, 8, 10, 12, 0, 0),
        "prompt_tokens": 100,
        "completion_tokens": 200,
        "cost": "0.05",
        "latency_ms": 350,
    }
    values.update(overrides)
    return RelayRequestLogEntry(**values)


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

    async def table_exists(self, table_name: str) -> bool:
        rows = self._result(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            [table_name],
        )
        return bool(rows.rows)


async def test_append_persists_redaction_safe_columns() -> None:
    db = SqliteFakeDatabase()
    store: RelayRequestLogStoreProtocol = SqlRelayRequestLogStore(db=db)
    await store.append(make_entry())
    rows = db._conn.execute(
        "SELECT request_id, user_id, model, status, prompt_tokens FROM ai_relay_request_logs"
    ).fetchall()
    assert len(rows) == 1
    assert rows[0]["request_id"] == "req-1"
    assert rows[0]["model"] == "gpt-4"
    assert rows[0]["status"] == "completed"
    assert rows[0]["prompt_tokens"] == 100


async def test_append_duplicate_request_id_is_idempotent() -> None:
    db = SqliteFakeDatabase()
    store: RelayRequestLogStoreProtocol = SqlRelayRequestLogStore(db=db)
    await store.append(make_entry())
    await store.append(make_entry(prompt_tokens=999))
    rows = db._conn.execute(
        "SELECT COUNT(*) AS n FROM ai_relay_request_logs"
    ).fetchone()
    assert rows["n"] == 1


async def test_daily_usage_aggregates_tokens_and_cost_per_day() -> None:
    db = SqliteFakeDatabase()
    store: RelayRequestLogStoreProtocol = SqlRelayRequestLogStore(db=db)
    await store.append(
        make_entry(request_id="r1", prompt_tokens=10, completion_tokens=20, cost="0.05")
    )
    await store.append(
        make_entry(request_id="r2", prompt_tokens=30, completion_tokens=40, cost="0.15")
    )
    await store.append(
        make_entry(
            request_id="r3",
            created_at=datetime(2026, 8, 9, 9, 0, 0),
            prompt_tokens=5,
            completion_tokens=5,
            cost="0.01",
        )
    )
    service: RelayUsageServiceProtocol = RelayUsageService(db=db)
    with clock.use(FixedClock(datetime(2026, 8, 10, 12, 0, 0, tzinfo=timezone.utc))):
        usage = await service.daily_usage(user_id="u1", days=7)
    assert len(usage) == 2
    by_day = {u.day: u for u in usage}
    today = by_day["2026-08-10"]
    assert isinstance(today, RelayDailyUsage)
    assert today.prompt_tokens == 40
    assert today.completion_tokens == 60
    assert today.cost == "0.2"
    assert by_day["2026-08-09"].completion_tokens == 5


async def test_daily_usage_other_users_are_ignored() -> None:
    db = SqliteFakeDatabase()
    store: RelayRequestLogStoreProtocol = SqlRelayRequestLogStore(db=db)
    await store.append(make_entry(user_id="u2"))
    service: RelayUsageServiceProtocol = RelayUsageService(db=db)
    usage = await service.daily_usage(user_id="u1", days=7)
    assert usage == []


async def test_model_rank_orders_by_completion_tokens() -> None:
    db = SqliteFakeDatabase()
    store: RelayRequestLogStoreProtocol = SqlRelayRequestLogStore(db=db)
    await store.append(
        make_entry(request_id="r1", model="gpt-4", completion_tokens=40, cost="0.05")
    )
    await store.append(
        make_entry(request_id="r2", model="claude-3", completion_tokens=90, cost="0.2")
    )
    await store.append(
        make_entry(request_id="r3", model="gpt-4", completion_tokens=10, cost="0.02")
    )
    service: RelayUsageServiceProtocol = RelayUsageService(db=db)
    rank = await service.model_rank(days=7, limit=5)
    assert isinstance(rank[0], RelayModelRank)
    assert [r.model for r in rank] == ["claude-3", "gpt-4"]
    assert rank[0].completion_tokens == 90
    assert rank[0].request_count == 1
    assert rank[1].completion_tokens == 50
    assert rank[1].request_count == 2
    assert rank[1].cost == "0.07"


async def test_model_rank_respects_limit_and_window() -> None:
    db = SqliteFakeDatabase()
    store: RelayRequestLogStoreProtocol = SqlRelayRequestLogStore(db=db)
    await store.append(make_entry(request_id="r1", model="gpt-4", completion_tokens=10))
    await store.append(
        make_entry(
            request_id="r2",
            model="claude-3",
            created_at=datetime(2026, 7, 1, 9, 0, 0),
            completion_tokens=500,
        )
    )
    service: RelayUsageServiceProtocol = RelayUsageService(db=db)
    rank = await service.model_rank(days=7, limit=1)
    assert len(rank) == 1
    assert rank[0].model == "gpt-4"


async def test_list_requests_round_trip_and_ordering() -> None:
    db = SqliteFakeDatabase()
    store: RelayRequestLogStoreProtocol = SqlRelayRequestLogStore(db=db)
    await store.append(
        make_entry(
            request_id="r1",
            created_at=datetime(2026, 8, 10, 9, 0, 0),
            prompt_tokens=10,
            completion_tokens=20,
            cost="0.05",
        )
    )
    await store.append(
        make_entry(
            request_id="r2",
            user_id="u2",
            token_id="t9",
            model="claude-3",
            status="failed",
            created_at=datetime(2026, 8, 10, 12, 0, 0),
            error_code="UPSTREAM_5XX",
        )
    )
    service: RelayUsageServiceProtocol = RelayUsageService(db=db)
    entries = await service.list_requests(days=7, page=1, page_size=20)
    assert [e.request_id for e in entries] == ["r2", "r1"]
    assert entries[0].user_id == "u2"
    assert entries[0].model == "claude-3"
    assert entries[0].status == "failed"
    assert entries[0].error_code == "UPSTREAM_5XX"
    assert entries[0].created_at == datetime(2026, 8, 10, 12, 0, 0)
    assert entries[1].cost == "0.05"


async def test_list_requests_filters_by_user_and_token() -> None:
    db = SqliteFakeDatabase()
    store: RelayRequestLogStoreProtocol = SqlRelayRequestLogStore(db=db)
    for i in range(3):
        await store.append(make_entry(request_id=f"r{i}", user_id="u1", token_id="t1"))
    await store.append(make_entry(request_id="rx", user_id="u2", token_id="t2"))
    service: RelayUsageServiceProtocol = RelayUsageService(db=db)
    entries = await service.list_requests(
        days=7, page=1, page_size=20, user_id="u1", token_id="t1"
    )
    assert [e.request_id for e in entries] == ["r2", "r1", "r0"]
    entries = await service.list_requests(days=7, page=1, page_size=20, user_id="u2")
    assert [e.request_id for e in entries] == ["rx"]


async def test_list_requests_paginates_and_respects_window() -> None:
    db = SqliteFakeDatabase()
    store: RelayRequestLogStoreProtocol = SqlRelayRequestLogStore(db=db)
    for i in range(3):
        await store.append(make_entry(request_id=f"r{i}", token_id="t1"))
    await store.append(
        make_entry(
            request_id="rold",
            token_id="t1",
            created_at=datetime(2026, 7, 1, 9, 0, 0),
        )
    )
    service: RelayUsageServiceProtocol = RelayUsageService(db=db)
    page_one = await service.list_requests(days=7, page=1, page_size=2)
    assert [e.request_id for e in page_one] == ["r2", "r1"]
    page_two = await service.list_requests(days=7, page=2, page_size=2)
    assert [e.request_id for e in page_two] == ["r0"]
    windowed = await service.list_requests(days=1, page=1, page_size=20)
    assert all(e.request_id != "rold" for e in windowed)
