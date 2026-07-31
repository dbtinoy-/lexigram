"""index_many sanitizes the index name before it reaches SQL (S608 closure).

The Postgres/MySQL backends interpolate the search index into
``INSERT INTO search_<index>``; the raw name is sanitized via
``_sanitize_index_name`` before any SQL is built.
"""

from __future__ import annotations

from typing import Any, Self

import pytest

from lexigram.search.backends.mysql.backend import MySQLDatabaseSearchBackend
from lexigram.search.backends.postgres.backend import PostgresDatabaseSearchBackend


class _FakeResult:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []


class _FakeConnection:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[Any]]] = []

    async def execute(self, sql: str, *params: Any) -> _FakeResult:
        """Record the call and return empty rows."""
        self.calls.append((sql, list(params)))
        return _FakeResult()


class _FakeProvider:
    def __init__(self) -> None:
        self.conn = _FakeConnection()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc: object) -> bool:
        return False

    def scoped_context(self) -> _FakeProvider:
        return self

    async def get_scoped_connection(self) -> _FakeConnection:
        return self.conn


_ATTACK = "news') ; DROP TABLE search_news;--"


@pytest.mark.asyncio
async def test_postgres_index_many_sanitizes_index() -> None:
    """A breakout payload in the index never reaches the INSERT."""
    provider = _FakeProvider()
    backend = PostgresDatabaseSearchBackend(provider=provider)

    await backend.index_many(
        documents=[("1", {"title": "test", "content": "body"})],
        index=_ATTACK,
    )

    sql = provider.conn.calls[-1][0]
    assert "DROP TABLE" not in sql
    assert "'" not in sql
    assert "search_news" in sql


@pytest.mark.asyncio
async def test_mysql_index_many_sanitizes_index() -> None:
    """A breakout payload in the index never reaches the INSERT."""
    provider = _FakeProvider()
    backend = MySQLDatabaseSearchBackend(provider=provider)

    await backend.index_many(
        documents=[("1", {"title": "test", "content": "body"})],
        index=_ATTACK,
    )

    sql = provider.conn.calls[-1][0]
    assert "DROP TABLE" not in sql
    assert "'" not in sql
    assert "search_news" in sql
