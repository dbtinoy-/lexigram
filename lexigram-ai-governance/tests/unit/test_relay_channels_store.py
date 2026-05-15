"""Tests for the SQL relay channel store with revision compare-and-set."""

from __future__ import annotations

import sqlite3
from typing import Any

from lexigram.ai.governance.relay_channels import SqlRelayChannelStore
from lexigram.contracts.ai.relay import RelayChannel, RelayFormat
from lexigram.contracts.ai.relay.store import RelayChannelStoreProtocol
from lexigram.contracts.data import DatabaseProviderProtocol, QueryResult


def make_channel(name: str = "c1", **overrides: Any) -> RelayChannel:
    """Build a RelayChannel with a sane default configuration."""
    values: dict[str, Any] = {
        "name": name,
        "upstream_base_url": "https://upstream.example",
        "target_format": RelayFormat.OPENAI_CHAT,
        "models": ("m1", "m2"),
        "capabilities": frozenset({"stream"}),
        "endpoint_kinds": frozenset({"chat"}),
        "priority": 50,
        "enabled": True,
    }
    values.update(overrides)
    return RelayChannel(**values)


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


async def test_upsert_inserts_and_bumps_revision() -> None:
    db = SqliteFakeDatabase()
    store: RelayChannelStoreProtocol = SqlRelayChannelStore(db=db)
    first = await store.upsert(make_channel())
    assert first == 1
    second = await store.upsert(make_channel(priority=10), expected_revision=1)
    assert second == 2
    snapshots = await store.list_channels()
    assert len(snapshots) == 1
    snapshot = snapshots[0]
    assert snapshot.revision == 2
    assert snapshot.channel.priority == 10
    assert snapshot.channel.target_format == RelayFormat.OPENAI_CHAT
    assert snapshot.channel.capabilities == frozenset({"stream"})
    assert snapshot.channel.endpoint_kinds == frozenset({"chat"})
    assert snapshot.channel.enabled is True
    assert snapshot.created_at <= snapshot.updated_at


async def test_upsert_rejects_stale_write() -> None:
    db = SqliteFakeDatabase()
    store: RelayChannelStoreProtocol = SqlRelayChannelStore(db=db)
    await store.upsert(make_channel())
    stale = await store.upsert(make_channel(priority=99), expected_revision=7)
    assert stale is None
    snapshots = await store.list_channels()
    assert snapshots[0].revision == 1
    assert snapshots[0].channel.priority == 50


async def test_upsert_rejects_explicit_revision_for_new_name() -> None:
    db = SqliteFakeDatabase()
    store: RelayChannelStoreProtocol = SqlRelayChannelStore(db=db)
    result = await store.upsert(make_channel(), expected_revision=1)
    assert result is None
    assert await store.list_channels() == []


async def test_delete_requires_matching_revision() -> None:
    db = SqliteFakeDatabase()
    store: RelayChannelStoreProtocol = SqlRelayChannelStore(db=db)
    await store.upsert(make_channel())
    stale = await store.delete("c1", expected_revision=5)
    assert stale is False
    deleted = await store.delete("c1", expected_revision=1)
    assert deleted is True
    assert await store.list_channels() == []


async def test_delete_missing_channel_returns_false() -> None:
    db = SqliteFakeDatabase()
    store: RelayChannelStoreProtocol = SqlRelayChannelStore(db=db)
    assert await store.delete("ghost", expected_revision=1) is False


async def test_list_round_trips_multiple_channels() -> None:
    db = SqliteFakeDatabase()
    store: RelayChannelStoreProtocol = SqlRelayChannelStore(db=db)
    await store.upsert(make_channel("alpha", models=("ma",), enabled=False))
    await store.upsert(
        make_channel(
            "beta",
            target_format=RelayFormat.CLAUDE,
            models=("mb",),
            priority=10,
        )
    )
    snapshots = await store.list_channels()
    assert [s.channel.name for s in snapshots] == ["alpha", "beta"]
    by_name = {s.channel.name: s for s in snapshots}
    assert by_name["alpha"].channel.enabled is False
    assert by_name["beta"].channel.target_format == RelayFormat.CLAUDE
    assert by_name["beta"].channel.priority == 10
    assert by_name["beta"].revision == 1