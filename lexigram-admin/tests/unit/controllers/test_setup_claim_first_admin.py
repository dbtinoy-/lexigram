"""Tests for atomic claim_first_admin (F2: TOCTOU narrowing).

Two simultaneous first-admin submissions must yield exactly one winner.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.admin.auth.errors import SetupAlreadyCompletedError
from lexigram.admin.auth.store.memory import MemoryAdminUserStore


class _QueryResult:
    """Minimal QueryResult-shaped stub for db_provider.execute."""

    def __init__(
        self, rows: list[dict] | None = None, row_count: int = 0, success: bool = True
    ) -> None:
        self.rows = rows or []
        self.row_count = row_count
        self.success = success


@pytest.mark.asyncio
async def test_memory_store_claim_first_admin_exactly_one_wins() -> None:
    """Two simultaneous claims against the memory store: one Ok, one Err."""
    store = MemoryAdminUserStore(config=SimpleNamespace(users=[]))

    results = await asyncio.gather(
        store.claim_first_admin(
            name="Admin A",
            email="a@test.com",
            hashed_password="hash-a",
            roles=["superadmin"],
        ),
        store.claim_first_admin(
            name="Admin B",
            email="b@test.com",
            hashed_password="hash-b",
            roles=["superadmin"],
        ),
    )

    oks = [r for r in results if r.is_ok()]
    errs = [r for r in results if r.is_err()]
    assert len(oks) == 1
    assert len(errs) == 1
    assert isinstance(errs[0].unwrap_err(), SetupAlreadyCompletedError)
    assert await store.count() == 1


@pytest.mark.asyncio
async def test_memory_store_sequential_second_claim_returns_err() -> None:
    """A second claim after the first succeeds is refused."""
    store = MemoryAdminUserStore(config=SimpleNamespace(users=[]))

    first = await store.claim_first_admin(
        name="Admin A",
        email="a@test.com",
        hashed_password="hash-a",
        roles=["superadmin"],
    )
    second = await store.claim_first_admin(
        name="Admin B",
        email="b@test.com",
        hashed_password="hash-b",
        roles=["superadmin"],
    )

    assert first.is_ok()
    assert second.is_err()
    assert isinstance(second.unwrap_err(), SetupAlreadyCompletedError)


@pytest.mark.asyncio
async def test_direct_sql_claim_first_admin_concurrent_single_insert() -> None:
    """Direct SQL claim: the second caller observes a non-empty table."""
    from lexigram.admin.auth.store.direct_sql import DirectSQLAdminUserStore

    insert_calls = 0

    async def fake_execute(sql: str, params: list | None = None) -> _QueryResult:
        nonlocal insert_calls
        sql_upper = sql.strip().upper()
        if "CREATE TABLE" in sql_upper:
            return _QueryResult()
        if "INSERT" in sql_upper:
            if insert_calls == 0:
                insert_calls += 1
                return _QueryResult(
                    rows=[
                        {
                            "id": "u-1",
                            "name": "Admin A",
                            "email": "a@test.com",
                        }
                    ],
                    row_count=1,
                )
            insert_calls += 1
            return _QueryResult(row_count=0)
        return _QueryResult()

    db_provider = MagicMock()
    db_provider.execute = AsyncMock(side_effect=fake_execute)
    db_provider.execute_query = AsyncMock(return_value=_QueryResult())

    store = DirectSQLAdminUserStore(db_provider=db_provider)

    results = await asyncio.gather(
        store.claim_first_admin(
            name="Admin A",
            email="a@test.com",
            hashed_password="hash-a",
            roles=["superadmin"],
        ),
        store.claim_first_admin(
            name="Admin B",
            email="b@test.com",
            hashed_password="hash-b",
            roles=["superadmin"],
        ),
    )

    oks = [r for r in results if r.is_ok()]
    errs = [r for r in results if r.is_err()]
    assert len(oks) == 1
    assert len(errs) == 1
    assert isinstance(errs[0].unwrap_err(), SetupAlreadyCompletedError)
    assert insert_calls == 2
