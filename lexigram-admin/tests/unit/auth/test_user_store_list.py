"""Unit tests for AdminUserStoreProtocol.list_users (direct SQL store)."""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.admin.auth.store.direct_sql import DirectSQLAdminUserStore


class _Rows:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows


class _Exec:
    def __init__(self, row_count: int = 1) -> None:
        self.row_count = row_count


class FakeDb:
    """In-memory DatabaseProviderProtocol double."""

    def __init__(self) -> None:
        self.executed: list[tuple[str, list[Any]]] = []
        self.rows: list[dict[str, Any]] = []

    async def execute(self, query: str, parameters: list[Any]) -> Any:
        self.executed.append((query, parameters))
        return _Exec()

    async def execute_query(self, query: str, parameters: list[Any]) -> Any:
        self.executed.append((query, parameters))
        return _Rows(self.rows)


def _user_row(user_id: str, email: str, roles: list[str]) -> dict[str, Any]:
    return {
        "id": user_id,
        "username": email,
        "email": email,
        "hashed_password": "hash",
        "roles": "{" + ",".join(roles) + "}",
        "permissions": "{}",
        "is_active": True,
        "is_verified": True,
        "created_at": "2026-08-14T00:00:00+00:00",
        "updated_at": "2026-08-14T00:00:00+00:00",
    }


def _store(db: FakeDb) -> DirectSQLAdminUserStore:
    return DirectSQLAdminUserStore(db_provider=db)  # param name as in __init__


@pytest.mark.asyncio
async def test_list_users_returns_records() -> None:
    db = FakeDb()
    db.rows = [
        _user_row("u1", "a@example.com", ["admin"]),
        _user_row("u2", "b@example.com", []),
    ]
    store = _store(db)

    users = await store.list_users()

    assert len(users) == 2
    assert users[0].email == "a@example.com"
    assert users[0].roles == ["admin"]
    assert users[1].user_id == "u2"


@pytest.mark.asyncio
async def test_list_users_orders_by_created_at() -> None:
    db = FakeDb()
    db.rows = [_user_row("u1", "a@example.com", [])]
    store = _store(db)

    await store.list_users()

    assert "ORDER BY created_at" in db.executed[0][0]


@pytest.mark.asyncio
async def test_list_users_empty_returns_empty() -> None:
    db = FakeDb()
    store = _store(db)

    assert await store.list_users() == []
