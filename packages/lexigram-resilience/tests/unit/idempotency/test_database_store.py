"""Unit tests for the SQL-backed idempotency store.

Covers the dialect-aware placeholder translation (audit §60): SQLite keeps
``?`` placeholders untouched, Postgres gets sequentially numbered ``$1..$N``.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import pytest

from lexigram.resilience.idempotency.database import (
    _ACQUIRE_SQL,
    _DELETE_SQL,
    _GET_SQL,
    _PURGE_EXPIRED_SQL,
    _SET_SQL,
    DatabaseIdempotencyStore,
    _translate_placeholders,
)


class FakeConnection:
    """Records every query executed by the store."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    async def fetch(
        self,
        query: str,
        *args: Any,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        self.calls.append((query, args))
        return []

    async def execute(self, query: str, *args: Any, **kwargs: Any) -> str:
        self.calls.append((query, args))
        return "INSERT 0 1"


class FakeProvider:
    """Fake DatabaseProviderProtocol with a configurable backend type."""

    def __init__(self, database_type: str = "sqlite") -> None:
        self.database_type = database_type
        self.connection = FakeConnection()

    @asynccontextmanager
    async def scoped_context(self) -> AsyncGenerator[FakeProvider, None]:
        yield self

    async def get_scoped_connection(self) -> FakeConnection:
        return self.connection


class TestTranslatePlaceholders:
    """Unit tests for the sequential placeholder translator."""

    def test_sqlite_is_a_no_op(self) -> None:
        assert _translate_placeholders(_GET_SQL, "sqlite") == _GET_SQL
        assert _translate_placeholders(_SET_SQL, "sqlite") == _SET_SQL
        assert _translate_placeholders(_DELETE_SQL, "sqlite") == _DELETE_SQL
        assert (
            _translate_placeholders(_PURGE_EXPIRED_SQL, "sqlite") == _PURGE_EXPIRED_SQL
        )
        assert _translate_placeholders(_ACQUIRE_SQL, "sqlite") == _ACQUIRE_SQL

    def test_unknown_dialect_falls_back_to_sqlite(self) -> None:
        assert _translate_placeholders(_GET_SQL, "mysql") == _GET_SQL
        assert _translate_placeholders(_SET_SQL, "unknown") == _SET_SQL

    def test_postgres_single_placeholder(self) -> None:
        assert _translate_placeholders(_GET_SQL, "postgres") == (
            "SELECT result, expires_at FROM idempotency_keys WHERE key = $1"
        )
        assert _translate_placeholders(_DELETE_SQL, "postgres") == (
            "DELETE FROM idempotency_keys WHERE key = $1"
        )
        assert _translate_placeholders(_PURGE_EXPIRED_SQL, "postgres") == (
            "DELETE FROM idempotency_keys WHERE expires_at IS NOT NULL "
            "AND expires_at <= $1"
        )

    def test_postgres_set_uses_sequential_placeholders(self) -> None:
        translated = _translate_placeholders(_SET_SQL, "postgres")

        assert "VALUES ($1, $2, $3, $4)" in translated
        assert "?" not in translated

    def test_postgres_acquire_uses_sequential_placeholders(self) -> None:
        translated = _translate_placeholders(_ACQUIRE_SQL, "postgres")

        assert "VALUES ($1, '__pending__', $2, $3)" in translated
        assert "?" not in translated

    def test_postgresql_enum_value_also_translates(self) -> None:
        translated = _translate_placeholders(_SET_SQL, "postgresql")

        assert "VALUES ($1, $2, $3, $4)" in translated


class TestDatabaseIdempotencyStoreDialects:
    """The store sends dialect-correct SQL to the injected provider."""

    @pytest.mark.asyncio
    async def test_postgres_set_sends_numbered_placeholders(self) -> None:
        provider = FakeProvider(database_type="postgres")
        store = DatabaseIdempotencyStore(db=provider)

        await store.set("key-1", {"ok": True}, ttl=60)

        sql, args = provider.connection.calls[1]
        assert "VALUES ($1, $2, $3, $4)" in sql
        assert len(args) == 4

    @pytest.mark.asyncio
    async def test_postgres_acquire_sends_numbered_placeholders(self) -> None:
        provider = FakeProvider(database_type="postgres")
        store = DatabaseIdempotencyStore(db=provider)

        acquired = await store.acquire("key-2", ttl=60)

        assert acquired is True
        sql, args = provider.connection.calls[1]
        assert "VALUES ($1, '__pending__', $2, $3)" in sql
        assert len(args) == 3

    @pytest.mark.asyncio
    async def test_postgres_single_placeholder_queries(self) -> None:
        provider = FakeProvider(database_type="postgres")
        store = DatabaseIdempotencyStore(db=provider)

        await store.get("key-3")
        await store.delete("key-3")
        await store.purge_expired()

        for sql, args in provider.connection.calls[1:]:
            assert "?" not in sql
            assert "$1" in sql
            assert len(args) == 1

    @pytest.mark.asyncio
    async def test_postgres_cleanup_expired_sends_numbered_placeholder(self) -> None:
        provider = FakeProvider(database_type="postgres")
        store = DatabaseIdempotencyStore(db=provider)

        removed = await store.cleanup_expired()

        assert removed == 1
        sql, args = provider.connection.calls[1]
        assert sql.endswith("<= $1")
        assert len(args) == 1

    @pytest.mark.asyncio
    async def test_sqlite_keeps_question_placeholders(self) -> None:
        provider = FakeProvider(database_type="sqlite")
        store = DatabaseIdempotencyStore(db=provider)

        await store.set("key-4", {"ok": True}, ttl=60)
        await store.acquire("key-5", ttl=60)
        await store.get("key-4")

        for sql, _args in provider.connection.calls[1:]:
            assert "?" in sql
            assert "$" not in sql

    @pytest.mark.asyncio
    async def test_provider_without_database_type_defaults_to_sqlite(self) -> None:
        provider = FakeProvider()
        delattr(provider, "database_type")
        store = DatabaseIdempotencyStore(db=provider)

        await store.set("key-6", "value")

        sql, _args = provider.connection.calls[1]
        assert "?" in sql
        assert "$" not in sql
