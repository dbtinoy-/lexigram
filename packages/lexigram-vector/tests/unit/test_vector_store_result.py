"""Unit tests for VectorStoreProtocol Result[T, E] pattern.

Tests that all MockVectorStore operations (add, search, delete) correctly
return Result[T, E] rather than raising exceptions or returning raw values.
"""

from __future__ import annotations

import pytest

from lexigram.contracts.ai.vector import Document
from lexigram.vector.testing.mocks import MockVectorStore


# ---------------------------------------------------------------------------
# MockVectorStore — add()
# ---------------------------------------------------------------------------


class TestVectorStoreAddResult:
    @pytest.mark.asyncio
    async def test_add_returns_ok_with_document_ids(self):
        store = MockVectorStore()
        docs = [
            Document(id="doc1", text="First document"),
            Document(id="doc2", text="Second document"),
        ]

        result = await store.add(docs)

        assert result.is_ok()
        ids = result.unwrap()
        assert "doc1" in ids
        assert "doc2" in ids
        assert len(ids) == 2

    @pytest.mark.asyncio
    async def test_add_auto_generates_id_when_missing(self):
        store = MockVectorStore()
        docs = [Document(text="No ID provided")]  # id=None

        result = await store.add(docs)

        assert result.is_ok()
        ids = result.unwrap()
        assert len(ids) == 1
        # Auto-generated ID is a non-empty string (UUID)
        assert isinstance(ids[0], str)
        assert len(ids[0]) > 0

    @pytest.mark.asyncio
    async def test_add_empty_list_returns_ok_with_empty_ids(self):
        store = MockVectorStore()

        result = await store.add([])

        assert result.is_ok()
        assert result.unwrap() == []

    @pytest.mark.asyncio
    async def test_add_preserves_metadata(self):
        store = MockVectorStore()
        docs = [Document(id="meta-doc", text="Demo", metadata={"source": "unit-test"})]

        await store.add(docs)

        # Verify document is stored with metadata
        assert "meta-doc" in store._documents
        assert store._documents["meta-doc"].metadata == {"source": "unit-test"}

    @pytest.mark.asyncio
    async def test_add_multiple_batches_accumulate(self):
        store = MockVectorStore()
        batch1 = [Document(id="a", text="doc a")]
        batch2 = [Document(id="b", text="doc b"), Document(id="c", text="doc c")]

        r1 = await store.add(batch1)
        r2 = await store.add(batch2)

        assert r1.is_ok()
        assert r2.is_ok()
        assert store.get_document_count() == 3


# ---------------------------------------------------------------------------
# MockVectorStore — search()
# ---------------------------------------------------------------------------


class TestVectorStoreRAGSearchResult:
    @pytest.mark.asyncio
    async def test_search_returns_ok_with_results(self):
        store = MockVectorStore()
        await store.add([
            Document(id="d1", text="Hello world"),
            Document(id="d2", text="Goodbye world"),
        ])

        result = await store.search(query_vector=[], k=10)

        assert result.is_ok()
        results = result.unwrap()
        assert isinstance(results, list)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_returns_ok_empty_when_no_documents(self):
        store = MockVectorStore()

        result = await store.search(query_vector=[], k=5)

        assert result.is_ok()
        assert result.unwrap() == []

    @pytest.mark.asyncio
    async def test_search_result_contains_search_result_objects(self):
        from lexigram.contracts.ai.vector import RAGSearchResult

        store = MockVectorStore()
        await store.add([Document(id="x", text="some text")])

        result = await store.search(query_vector=[], k=5)

        assert result.is_ok()
        items = result.unwrap()
        assert len(items) == 1
        assert isinstance(items[0], RAGSearchResult)
        assert items[0].document.id == "x"
        assert items[0].score == 1.0  # First result gets score 1.0
        assert items[0].rank == 0

    @pytest.mark.asyncio
    async def test_search_respects_top_k_limit(self):
        store = MockVectorStore()
        await store.add([Document(id=str(i), text=f"doc {i}") for i in range(10)])

        result = await store.search(query_vector=[], k=3)

        assert result.is_ok()
        assert len(result.unwrap()) == 3

    @pytest.mark.asyncio
    async def test_search_filters_by_metadata(self):
        store = MockVectorStore()
        await store.add([
            Document(id="a1", text="answer A", metadata={"category": "a"}),
            Document(id="b1", text="answer B", metadata={"category": "b"}),
            Document(id="a2", text="another A", metadata={"category": "a"}),
        ])

        result = await store.search(query_vector=[], k=10, filter={"category": "a"})

        assert result.is_ok()
        docs = result.unwrap()
        assert len(docs) == 2
        for item in docs:
            assert item.document.metadata.get("category") == "a"

    @pytest.mark.asyncio
    async def test_search_scores_decrease_for_lower_ranked_results(self):
        store = MockVectorStore()
        await store.add([
            Document(id="1", text="first"),
            Document(id="2", text="second"),
            Document(id="3", text="third"),
        ])

        result = await store.search(query_vector=[], k=3)

        assert result.is_ok()
        items = result.unwrap()
        scores = [item.score for item in items]
        # Scores should be non-increasing
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1]


# ---------------------------------------------------------------------------
# MockVectorStore — delete()
# ---------------------------------------------------------------------------


class TestVectorStoreDeleteResult:
    @pytest.mark.asyncio
    async def test_delete_returns_ok_with_count(self):
        store = MockVectorStore()
        await store.add([
            Document(id="del1", text="to delete"),
            Document(id="del2", text="also delete"),
            Document(id="keep", text="keep this"),
        ])

        result = await store.delete(["del1", "del2"])

        assert result.is_ok()
        assert result.unwrap() == 2

    @pytest.mark.asyncio
    async def test_delete_removes_documents_from_store(self):
        store = MockVectorStore()
        await store.add([Document(id="remove-me", text="remove")])

        await store.delete(["remove-me"])

        assert "remove-me" not in store._documents
        assert store.get_document_count() == 0

    @pytest.mark.asyncio
    async def test_delete_missing_id_returns_ok_with_zero_count(self):
        store = MockVectorStore()

        result = await store.delete(["nonexistent-id"])

        assert result.is_ok()
        assert result.unwrap() == 0

    @pytest.mark.asyncio
    async def test_delete_empty_list_returns_ok_with_zero(self):
        store = MockVectorStore()
        await store.add([Document(id="d", text="doc")])

        result = await store.delete([])

        assert result.is_ok()
        assert result.unwrap() == 0
        assert store.get_document_count() == 1

    @pytest.mark.asyncio
    async def test_delete_partial_match_returns_correct_count(self):
        store = MockVectorStore()
        await store.add([
            Document(id="exist1", text="exists"),
            Document(id="exist2", text="also exists"),
        ])

        # One existing, one missing
        result = await store.delete(["exist1", "phantom-id"])

        assert result.is_ok()
        assert result.unwrap() == 1
        assert store.get_document_count() == 1


# ---------------------------------------------------------------------------
# Round-trip: add → search → delete
# ---------------------------------------------------------------------------


class TestVectorStoreRoundTrip:
    @pytest.mark.asyncio
    async def test_full_round_trip(self):
        store = MockVectorStore()

        # Add
        add_result = await store.add([
            Document(id="rt1", text="Round trip document", metadata={"tag": "test"}),
        ])
        assert add_result.is_ok()
        assert store.get_document_count() == 1

        # Search
        search_result = await store.search(query_vector=[], k=5)
        assert search_result.is_ok()
        items = search_result.unwrap()
        assert len(items) == 1
        assert items[0].document.id == "rt1"
        assert items[0].document.text == "Round trip document"

        # Delete
        delete_result = await store.delete(["rt1"])
        assert delete_result.is_ok()
        assert delete_result.unwrap() == 1
        assert store.get_document_count() == 0

        # Search after delete
        empty_result = await store.search(query_vector=[], k=5)
        assert empty_result.is_ok()
        assert empty_result.unwrap() == []
