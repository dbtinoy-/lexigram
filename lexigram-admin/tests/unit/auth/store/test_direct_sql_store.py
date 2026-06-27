"""Admin user store: public ensure_schema + protocol conformance (spec Step 3)."""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.admin.auth.store import DirectSQLAdminUserStore
from lexigram.admin.auth.store.memory import MemoryAdminUserStore
from lexigram.admin.auth.store.protocols import AdminUserStoreProtocol


class FakeDbProvider:
    """Minimal DatabaseProviderProtocol fake that records executed SQL."""

    def __init__(self) -> None:
        self.database_type = "postgres"
        self.executed: list[str] = []
        self.create_user_called = False

    async def execute(self, sql: str, params: Any = None) -> Any:
        self.executed.append(sql)
        return []

    async def execute_query(self, sql: str, params: Any = None) -> Any:
        self.executed.append(sql)
        if "SELECT EXISTS" in sql:
            return [{"exists": False}]
        return []


@pytest.mark.asyncio
async def test_ensure_schema_is_public_and_idempotent() -> None:
    db = FakeDbProvider()
    store = DirectSQLAdminUserStore(db_provider=db)
    await store.ensure_schema()
    statements_after_first = list(db.executed)
    await store.ensure_schema()
    assert [s for s in statements_after_first if "CREATE TABLE" in s]
    assert db.executed == statements_after_first


@pytest.mark.asyncio
async def test_ensure_schema_does_not_duplicate_table_on_existing() -> None:
    db = FakeDbProvider()

    async def _existing(self_sql: str, params: Any = None) -> Any:
        return [{"exists": True}]

    db.execute_query = _existing  # type: ignore[method-assign]
    store = DirectSQLAdminUserStore(db_provider=db)
    await store.ensure_schema()
    assert not any("CREATE TABLE" in sql for sql in db.executed)


def test_admin_user_store_protocol_declares_ensure_schema() -> None:
    assert "ensure_schema" in AdminUserStoreProtocol.__dict__


def test_memory_store_satisfies_protocol() -> None:
    assert all(
        hasattr(MemoryAdminUserStore, name)
        for name in ("ensure_schema", "get_by_email", "authenticate")
    )


def test_direct_sql_store_implements_ensure_schema() -> None:
    assert callable(getattr(DirectSQLAdminUserStore, "ensure_schema", None))
