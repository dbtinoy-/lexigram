"""Tests — real composition root, no mocks.

Every test boots a real Application with the actual DI container.
Services are tested through their public API, not by mocking internals.
"""

from __future__ import annotations

import pytest
import httpx


class TestDocumentIngestion:
    """Test document ingestion endpoints."""

    @pytest.mark.asyncio
    async def test_ingest_document(self, client: httpx.AsyncClient) -> None:
        """POST /api/rag/ingest ingests a document."""
        resp = await client.post(
            "/api/rag/ingest",
            json={"content": "This is a test document about Python programming.", "metadata": {"source": "api"}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["chunks_stored"] == 1
        assert len(data["document_ids"]) == 1

    @pytest.mark.asyncio
    async def test_ingest_empty_content(self, client: httpx.AsyncClient) -> None:
        """POST /api/rag/ingest with empty content returns error."""
        resp = await client.post(
            "/api/rag/ingest",
            json={"content": ""},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_ingest_large_document(self, client: httpx.AsyncClient) -> None:
        """POST /api/rag/ingest chunks large documents."""
        content = " ".join(["word"] * 1000)  # 1000 words
        resp = await client.post(
            "/api/rag/ingest",
            json={"content": content, "metadata": {"source": "test"}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["chunks_stored"] > 1


class TestDocumentSearch:
    """Test document search endpoints."""

    @pytest.mark.asyncio
    async def test_search_documents(self, client: httpx.AsyncClient) -> None:
        """POST /api/rag/search searches documents."""
        # Ingest a document first
        await client.post(
            "/api/rag/ingest",
            json={"content": "Python is a programming language.", "metadata": {"source": "api"}},
        )

        resp = await client.post(
            "/api/rag/search",
            json={"query": "Python programming"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["query"] == "Python programming"
        assert data["count"] >= 1

    @pytest.mark.asyncio
    async def test_search_empty_query(self, client: httpx.AsyncClient) -> None:
        """POST /api/rag/search with empty query returns error."""
        resp = await client.post(
            "/api/rag/search",
            json={"query": ""},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_search_with_context(self, client: httpx.AsyncClient) -> None:
        """POST /api/rag/search/context returns formatted context."""
        # Ingest a document first
        await client.post(
            "/api/rag/ingest",
            json={"content": "Python is a programming language.", "metadata": {"source": "api"}},
        )

        resp = await client.post(
            "/api/rag/search/context",
            json={"query": "Python programming"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "query" in data
        assert "context" in data
        assert "sources" in data


class TestStats:
    """Test stats endpoint."""

    @pytest.mark.asyncio
    async def test_get_stats(self, client: httpx.AsyncClient) -> None:
        """GET /api/rag/stats returns stats."""
        resp = await client.get("/api/rag/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_documents" in data
        assert "top_k" in data


class TestHealth:
    """Test health endpoint."""

    @pytest.mark.asyncio
    async def test_health(self, client: httpx.AsyncClient) -> None:
        """GET /api/rag/health returns ok."""
        resp = await client.get("/api/rag/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
