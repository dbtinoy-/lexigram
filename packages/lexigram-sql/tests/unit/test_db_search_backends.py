"""Unit tests for database-backed search backends.

Tests for PostgresDatabaseSearchBackend and MySQLDatabaseSearchBackend
now living in lexigram-search.  All database interactions are mocked via
AsyncMock so these tests run without a real database.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.search.backends.mysql import MySQLDatabaseSearchBackend
from lexigram.search.backends.postgres import PostgresDatabaseSearchBackend

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_db_provider(execute_return: object = None) -> MagicMock:
    """Return a mock DatabaseProviderProtocol that yields a fake connection."""
    conn = MagicMock()
    conn.execute = AsyncMock(return_value=execute_return or MagicMock(rows=[]))

    provider = MagicMock()
    provider.connect = AsyncMock()
    provider.disconnect = AsyncMock()

    # scoped_context() is an async context manager
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _scoped():
        yield

    provider.scoped_context = _scoped
    provider.get_scoped_connection = AsyncMock(return_value=conn)
    return provider, conn


# ===========================================================================
# PostgresDatabaseSearchBackend
# ===========================================================================


class TestPostgresDatabaseSearchBackend:
    """Tests for the Postgres FTS backend."""

    @pytest.fixture
    def provider_and_conn(self):
        return _make_db_provider()

    @pytest.fixture
    def backend(self, provider_and_conn):
        provider, _ = provider_and_conn
        return PostgresDatabaseSearchBackend(provider=provider)

    # --- helpers ---

    def test_sanitize_index_name(self, backend):
        """Hyphens, dots and spaces are replaced with underscores."""
        assert backend._sanitize_index_name("my-index") == "my_index"
        assert backend._sanitize_index_name("my.index") == "my_index"
        assert backend._sanitize_index_name("my index") == "my_index"
        assert backend._sanitize_index_name("a-b.c d") == "a_b_c_d"

    def test_extract_doc_id_from_id(self, backend):
        assert backend._extract_doc_id({"id": "abc"}) == "abc"

    def test_extract_doc_id_from_underscore_id(self, backend):
        assert backend._extract_doc_id({"_id": "xyz"}) == "xyz"

    def test_extract_doc_id_raises_on_missing(self, backend):
        with pytest.raises(ValueError, match="must have an 'id'"):
            backend._extract_doc_id({"title": "no id here"})

    def test_extract_searchable_text_priority_fields(self, backend):
        doc = {"id": "1", "title": "Hello", "description": "World", "foo": "bar"}
        text = backend._extract_searchable_text(doc)
        assert "Hello" in text
        assert "World" in text

    def test_extract_searchable_text_excludes_long_strings(self, backend):
        long = "x" * 300
        doc = {"id": "1", "title": "Short", "blob": long}
        text = backend._extract_searchable_text(doc)
        assert "Short" in text
        assert long not in text

    def test_prepare_document_adds_searchable(self, backend):
        doc = {"id": "1", "title": "Test"}
        prepared = backend._prepare_document(doc)
        assert "_searchable" in prepared
        assert "Test" in prepared["_searchable"]

    def test_prepare_document_preserves_existing_searchable(self, backend):
        doc = {"id": "1", "title": "Test", "_searchable": "custom"}
        prepared = backend._prepare_document(doc)
        assert prepared["_searchable"] == "custom"

    # --- lifecycle ---

    @pytest.mark.asyncio
    async def test_connect_delegates_to_provider(self, backend, provider_and_conn):
        provider, _ = provider_and_conn
        await backend.connect()
        provider.connect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_close_delegates_to_provider(self, backend, provider_and_conn):
        provider, _ = provider_and_conn
        await backend.close()
        provider.disconnect.assert_awaited_once()

    # --- schema management ---

    @pytest.mark.asyncio
    async def test_ensure_schema_creates_table_and_index(
        self, backend, provider_and_conn
    ):
        provider, conn = provider_and_conn
        await backend.ensure_schema("articles")
        assert conn.execute.call_count >= 2  # CREATE TABLE + CREATE INDEX

    @pytest.mark.asyncio
    async def test_create_index_delegates_to_ensure_table(
        self, backend, provider_and_conn
    ):
        provider, conn = provider_and_conn
        result = await backend.create_index("docs")
        assert result is True
        assert conn.execute.call_count >= 1

    @pytest.mark.asyncio
    async def test_delete_index_drops_table(self, backend, provider_and_conn):
        provider, conn = provider_and_conn
        result = await backend.delete_index("docs")
        assert result is True
        call_args = conn.execute.call_args[0][0]
        assert "DROP TABLE" in call_args

    # --- indexing ---

    @pytest.mark.asyncio
    async def test_index_document_upserts(self, backend, provider_and_conn):
        provider, conn = provider_and_conn
        result = await backend.index_document("posts", {"id": "1", "title": "A"})
        assert result["id"] == "1"
        assert result["status"] == "indexed"

    @pytest.mark.asyncio
    async def test_index_multiple_documents(self, backend, provider_and_conn):
        provider, conn = provider_and_conn
        docs = [{"id": "1", "title": "A"}, {"id": "2", "title": "B"}]
        result = await backend.index("posts", docs)
        assert result is True

    @pytest.mark.asyncio
    async def test_update_sets_id_and_upserts(self, backend, provider_and_conn):
        provider, conn = provider_and_conn
        result = await backend.update("posts", "42", {"title": "Updated"})
        assert result is True

    # --- deletion ---

    @pytest.mark.asyncio
    async def test_delete_document(self, backend, provider_and_conn):
        provider, conn = provider_and_conn
        mock_result = MagicMock(row_count=1)
        conn.execute.return_value = mock_result
        result = await backend.delete_document("posts", "1")
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_calls_delete_document(self, backend, provider_and_conn):
        provider, conn = provider_and_conn
        conn.execute.return_value = MagicMock(row_count=1)
        result = await backend.delete("posts", "1")
        assert result is True

    # --- search ---

    @pytest.mark.asyncio
    async def test_search_returns_search_response(self, backend, provider_and_conn):
        provider, conn = provider_and_conn
        conn.execute.return_value = MagicMock(rows=[])
        response = await backend.search("articles", "python")

        assert hasattr(response, "query")
        assert response.query == "python"
        assert hasattr(response, "results")
        assert response.results == []

    # --- health ---

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, backend, provider_and_conn):
        provider, conn = provider_and_conn
        result = await backend.health_check()
        from lexigram.contracts.core import HealthStatus

        assert result.status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_health_check_unhealthy_on_exception(
        self, backend, provider_and_conn
    ):
        provider, conn = provider_and_conn
        conn.execute.side_effect = RuntimeError("connection refused")
        result = await backend.health_check()
        from lexigram.contracts.core import HealthStatus

        assert result.status == HealthStatus.UNHEALTHY
        assert "connection refused" in (result.error or "")


# ===========================================================================
# MySQLDatabaseSearchBackend
# ===========================================================================


class TestMySQLDatabaseSearchBackend:
    """Tests for the MySQL FULLTEXT backend."""

    @pytest.fixture
    def provider_and_conn(self):
        return _make_db_provider()

    @pytest.fixture
    def backend(self, provider_and_conn):
        provider, _ = provider_and_conn
        return MySQLDatabaseSearchBackend(provider=provider)

    # --- helpers ---

    def test_sanitize_index_name(self, backend):
        assert (
            backend._sanitize_index_name("my-index.test name") == "my_index_test_name"
        )

    def test_extract_doc_id(self, backend):
        assert backend._extract_doc_id({"id": "1"}) == "1"
        assert backend._extract_doc_id({"_id": "2"}) == "2"

    def test_extract_doc_id_raises(self, backend):
        with pytest.raises(ValueError, match="must have an 'id'"):
            backend._extract_doc_id({})

    def test_extract_searchable_text(self, backend):
        doc = {"id": "1", "title": "MySQL FULLTEXT", "body": "test body"}
        text = backend._extract_searchable_text(doc)
        assert "MySQL FULLTEXT" in text
        assert "test body" in text

    # --- lifecycle ---

    @pytest.mark.asyncio
    async def test_connect(self, backend, provider_and_conn):
        provider, _ = provider_and_conn
        await backend.connect()
        provider.connect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_close(self, backend, provider_and_conn):
        provider, _ = provider_and_conn
        await backend.close()
        provider.disconnect.assert_awaited_once()

    # --- schema management ---

    @pytest.mark.asyncio
    async def test_ensure_schema(self, backend, provider_and_conn):
        provider, conn = provider_and_conn
        await backend.ensure_schema("articles")
        assert conn.execute.called

    @pytest.mark.asyncio
    async def test_create_index(self, backend, provider_and_conn):
        provider, conn = provider_and_conn
        result = await backend.create_index("docs")
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_index(self, backend, provider_and_conn):
        provider, conn = provider_and_conn
        result = await backend.delete_index("docs")
        assert result is True
        call_args = conn.execute.call_args[0][0]
        assert "DROP TABLE" in call_args

    # --- indexing ---

    @pytest.mark.asyncio
    async def test_index_document(self, backend, provider_and_conn):
        provider, conn = provider_and_conn
        result = await backend.index_document("pages", {"id": "p1", "title": "Test"})
        assert result["id"] == "p1"
        assert result["status"] == "indexed"

    @pytest.mark.asyncio
    async def test_index_multiple(self, backend, provider_and_conn):
        provider, conn = provider_and_conn
        result = await backend.index("pages", [{"id": "1"}, {"id": "2"}])
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_document(self, backend, provider_and_conn):
        provider, conn = provider_and_conn
        result = await backend.delete_document("pages", "p1")
        assert result is True

    # --- search ---

    @pytest.mark.asyncio
    async def test_search_returns_search_response(self, backend, provider_and_conn):
        provider, conn = provider_and_conn
        conn.execute.return_value = MagicMock(rows=[])
        response = await backend.search("pages", "mysql")
        from lexigram.search.types import SearchResponse

        assert isinstance(response, SearchResponse)
        assert response.query == "mysql"

    # --- health ---

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, backend, provider_and_conn):
        provider, conn = provider_and_conn
        result = await backend.health_check()
        from lexigram.contracts.core import HealthStatus

        assert result.status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, backend, provider_and_conn):
        provider, conn = provider_and_conn
        conn.execute.side_effect = RuntimeError("db down")
        result = await backend.health_check()
        from lexigram.contracts.core import HealthStatus

        assert result.status == HealthStatus.UNHEALTHY
