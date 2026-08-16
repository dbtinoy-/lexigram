"""Postgres faceted_search facet-key safety tests (F2)."""

from __future__ import annotations

from typing import Any, Self

import pytest

from lexigram.search.backends.postgres.backend import PostgresDatabaseSearchBackend


class _FakeResult:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows


class _FakeConnection:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[Any]]] = []

    async def execute(self, sql: str, *params: Any) -> _FakeResult:
        """Record the call and return empty rows."""
        self.calls.append((sql, list(params)))
        return _FakeResult([])


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


def _backend() -> tuple[PostgresDatabaseSearchBackend, _FakeProvider]:
    provider = _FakeProvider()
    return PostgresDatabaseSearchBackend(provider=provider), provider


async def test_valid_facet_builds_json_path() -> None:
    """A plain facet key renders document->>'status'."""
    backend, provider = _backend()

    result = await backend.faceted_search("news", "hello", facets=["status"])

    assert result["facets"] == {"status": []}
    facet_sql = provider.conn.calls[1][0]
    assert "document->>'status'" in facet_sql


async def test_malicious_facet_raises_and_never_executes() -> None:
    """A breakout payload in a facet key raises before any SQL runs."""
    backend, provider = _backend()

    with pytest.raises(ValueError, match="Invalid facet field"):
        await backend.faceted_search(
            "news", "hello", facets=["status", "title') UNION SELECT 1,2,3;--"]
        )

    assert provider.conn.calls == []


async def test_non_identifier_facets_all_raise() -> None:
    """Hyphenated, spaced, and empty facet keys are rejected."""
    backend, _ = _backend()

    for bad in ("x-x", "has space", ""):
        with pytest.raises(ValueError, match="Invalid facet field"):
            await backend.faceted_search("news", "hello", facets=[bad])


def test_sanitize_index_name_sanity() -> None:
    """Index-name sanitizer remains unchanged."""
    assert PostgresDatabaseSearchBackend._sanitize_index_name("my-index") == "my_index"
