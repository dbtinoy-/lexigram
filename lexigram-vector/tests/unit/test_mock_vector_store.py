"""Tests for mock vector store implementations."""

from __future__ import annotations

import pytest

from lexigram.contracts.ai.vector import Document
from lexigram.vector.testing.mocks import (
    MockVectorStore,
    MockVectorStoreWithErrors,
    MockVectorStoreWithSimilarity,
)


class TestMockVectorStore:
    """Test basic MockVectorStore functionality."""

    @pytest.mark.asyncio
    async def test_add_stores_documents(self):
        """Test that add() stores documents and returns IDs."""
        store = MockVectorStore()
        docs = [
            Document(text="Python is a programming language", id="1"),
            Document(text="JavaScript is for web development", id="2"),
        ]

        result = await store.add(docs)

        assert result.is_ok()
        ids = result.unwrap()
        assert len(ids) == 2
        assert store.get_document_count() == 2

    @pytest.mark.asyncio
    async def test_add_generates_ids(self):
        """Test that add() generates IDs when not provided."""
        store = MockVectorStore()
        docs = [
            Document(text="Test document"),
        ]

        result = await store.add(docs)

        assert result.is_ok()
        ids = result.unwrap()
        assert len(ids) == 1
        assert ids[0] is not None

    @pytest.mark.asyncio
    async def test_search_returns_results(self):
        """Test that search() returns scored results."""
        store = MockVectorStore()
        await store.add([
            Document(text="Python is a programming language", id="1"),
            Document(text="JavaScript is for web development", id="2"),
        ])

        result = await store.search(query_vector=[], top_k=2)

        assert result.is_ok()
        results = result.unwrap()
        assert len(results) == 2
        assert results[0].document.text is not None
        assert results[0].score >= 0.0

    @pytest.mark.asyncio
    async def test_search_respects_top_k(self):
        """Test that search() respects top_k parameter."""
        store = MockVectorStore()
        await store.add([
            Document(text="Doc 1", id="1"),
            Document(text="Doc 2", id="2"),
            Document(text="Doc 3", id="3"),
        ])

        result = await store.search(query_vector=[], top_k=2)

        assert result.is_ok()
        results = result.unwrap()
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_with_filters(self):
        """Test that search() respects metadata filters."""
        store = MockVectorStore()
        await store.add([
            Document(text="Python doc", id="1", metadata={"lang": "python"}),
            Document(text="JS doc", id="2", metadata={"lang": "javascript"}),
        ])

        result = await store.search(query_vector=[], top_k=5, filter={"lang": "python"})

        assert result.is_ok()
        results = result.unwrap()
        assert len(results) == 1
        assert results[0].document.metadata["lang"] == "python"

    @pytest.mark.asyncio
    async def test_delete_removes_document(self):
        """Test that delete() removes documents by ID."""
        store = MockVectorStore()
        await store.add([
            Document(text="Python doc", id="1"),
            Document(text="JS doc", id="2"),
        ])

        result = await store.delete(["1"])

        assert result.is_ok()
        assert result.unwrap() == 1
        assert store.get_document_count() == 1

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_zero(self):
        """Test that deleting nonexistent ID returns 0."""
        store = MockVectorStore()
        await store.add([Document(text="Python doc", id="1")])

        result = await store.delete(["nonexistent"])

        assert result.is_ok()
        assert result.unwrap() == 0

    @pytest.mark.asyncio
    async def test_clear_removes_all(self):
        """Test that clear() removes all documents."""
        store = MockVectorStore()
        await store.add([
            Document(text="Python doc", id="1"),
            Document(text="JS doc", id="2"),
        ])

        store.clear()

        assert store.get_document_count() == 0

    @pytest.mark.asyncio
    async def test_batch_upsert(self):
        """Test batch upsert functionality."""
        store = MockVectorStore()
        docs = [
            Document(text="Doc 1", id="1"),
            Document(text="Doc 2", id="2"),
            Document(text="Doc 3", id="3"),
        ]

        result = await store.batch_upsert(docs, batch_size=2)

        assert result.is_ok()
        assert result.unwrap() == 3
        assert store.get_document_count() == 3


class TestMockVectorStoreWithSimilarity:
    """Test MockVectorStoreWithSimilarity with cosine similarity."""

    @pytest.mark.asyncio
    async def test_similarity_calculation(self):
        """Test that cosine similarity calculation works correctly."""
        store = MockVectorStoreWithSimilarity()
        await store.add([
            Document(
                text="Similar to query",
                embedding=[0.1, 0.2, 0.3],
                id="1",
            ),
            Document(
                text="Different",
                embedding=[0.9, 0.9, 0.9],
                id="2",
            ),
        ])

        result = await store.search(query_vector=[0.1, 0.2, 0.3], top_k=2)

        assert result.is_ok()
        results = result.unwrap()
        assert len(results) == 2
        assert results[0].document.id == "1"
        assert results[0].score > results[1].score

    @pytest.mark.asyncio
    async def test_similarity_with_identical_vectors(self):
        """Test similarity with identical vectors gives score of 1."""
        store = MockVectorStoreWithSimilarity()
        embedding = [0.5, 0.5, 0.5]
        await store.add([
            Document(text="Doc 1", embedding=embedding, id="1"),
        ])

        result = await store.search(query_vector=embedding, top_k=1)

        assert result.is_ok()
        results = result.unwrap()
        assert len(results) == 1
        assert results[0].score == pytest.approx(1.0)

    @pytest.mark.asyncio
    async def test_similarity_threshold_filters_results(self):
        """Test that similarity_threshold filters low-scoring results."""
        store = MockVectorStoreWithSimilarity(similarity_threshold=0.5)
        await store.add([
            Document(text="High similarity", embedding=[0.1, 0.2, 0.3], id="1"),
            Document(text="Low similarity", embedding=[0.9, 0.9, 0.9], id="2"),
        ])

        result = await store.search(query_vector=[0.1, 0.2, 0.3], top_k=5)

        assert result.is_ok()
        results = result.unwrap()
        assert all(r.score >= 0.5 for r in results)


class TestMockVectorStoreWithErrors:
    """Test MockVectorStoreWithErrors for error handling."""

    @pytest.mark.asyncio
    async def test_search_error_propagates(self):
        """Test that error propagates from search."""
        store = MockVectorStoreWithErrors(fail_on_search=True)

        result = await store.search(query_vector=[], top_k=5)

        assert result.is_err()
        assert isinstance(result.unwrap_err(), Exception)

    @pytest.mark.asyncio
    async def test_add_error_propagates(self):
        """Test that error propagates from add."""
        store = MockVectorStoreWithErrors(fail_on_add=True)

        result = await store.add([Document(text="test", id="1")])

        assert result.is_err()

    @pytest.mark.asyncio
    async def test_delete_error_propagates(self):
        """Test that error propagates from delete."""
        store = MockVectorStoreWithErrors(fail_on_delete=True)

        result = await store.delete(["1"])

        assert result.is_err()

    @pytest.mark.asyncio
    async def test_custom_error_message(self):
        """Test custom error message."""
        store = MockVectorStoreWithErrors(
            fail_on_search=True,
            error_message="Custom search error",
        )

        result = await store.search(query_vector=[], top_k=5)

        assert result.is_err()
        assert "Custom search error" in str(result.unwrap_err())
