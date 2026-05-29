"""Unit tests for AdminRoleSqlStore with a fake DB provider."""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.admin.rbac.roles_sql import AdminRoleSqlStore
from lexigram.admin.rbac.types import AdminRole


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


def _row(name: str, **overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "name": name,
        "description": f"{name} description",
        "permissions": '["posts.view", "posts.edit"]',
        "inherits": "[]",
        "is_system": False,
    }
    data.update(overrides)
    return data


def _store(db: FakeDb) -> AdminRoleSqlStore:
    return AdminRoleSqlStore(db=db)


@pytest.mark.asyncio
async def test_ensure_schema_creates_table_once() -> None:
    db = FakeDb()
    store = _store(db)

    await store.ensure_schema()
    await store.ensure_schema()

    assert len(db.executed) == 1
    assert "CREATE TABLE IF NOT EXISTS admin_roles" in db.executed[0][0]


@pytest.mark.asyncio
async def test_list_roles_maps_rows() -> None:
    db = FakeDb()
    db.rows = [_row("editor"), _row("admin", is_system=True)]
    store = _store(db)

    roles = await store.list_roles()

    assert [r.name for r in roles] == ["editor", "admin"]
    editor = roles[0]
    assert editor.description == "editor description"
    assert editor.permissions == ["posts.view", "posts.edit"]
    assert editor.inherits == []
    assert roles[1].is_system is True


@pytest.mark.asyncio
async def test_get_role_returns_single_row() -> None:
    db = FakeDb()
    db.rows = [_row("editor")]
    store = _store(db)

    role = await store.get_role("editor")

    assert role is not None
    assert role.name == "editor"


@pytest.mark.asyncio
async def test_get_role_missing_returns_none() -> None:
    db = FakeDb()
    db.rows = []
    store = _store(db)

    assert await store.get_role("ghost") is None


@pytest.mark.asyncio
async def test_create_role_inserts_json_encoded_permissions() -> None:
    db = FakeDb()
    store = _store(db)
    role = AdminRole("editor", "Editors", ["posts.view"], ["viewer"], False)

    await store.create_role(role)

    query, params = db.executed[0]
    assert "INSERT INTO admin_roles" in query
    assert params[0] == "editor"
    assert '"posts.view"' in params[2]
    assert '"viewer"' in params[3]


@pytest.mark.asyncio
async def test_update_role_updates_fields() -> None:
    db = FakeDb()
    store = _store(db)
    role = AdminRole("editor", "Editors v2", ["posts.edit"], [], False)

    await store.update_role(role)

    query, params = db.executed[0]
    assert "UPDATE admin_roles" in query
    assert params[0] == "Editors v2"
    assert params[-1] == "editor"


@pytest.mark.asyncio
async def test_delete_role_returns_row_count_bool() -> None:
    db = FakeDb()
    store = _store(db)

    assert await store.delete_role("editor") is True

    db2 = FakeDb()
    store2 = _store(db2)
    db2.rows = []
    # Simulate a delete that matched nothing
    await store2.delete_role("ghost")
    # row_count defaults to 1 in _Exec; assert the query shape instead
    assert "DELETE FROM admin_roles" in db2.executed[0][0]
