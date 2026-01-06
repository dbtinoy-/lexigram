"""Unit tests for VectorStoreAdapter (AI-layer adaptor over infra VectorCollectionProtocol)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.ai.vector import Document, RAGSearchResult
from lexigram.contracts.core import HealthStatus
from lexigram.contracts.data.vector.types import (
    DeleteResult,
    SearchResult as InfraSearchResult,
    UpsertResult,
    VectorRecord,
)
from lexigram.vector.adapters.vector_store import VectorStoreAdapter
from lexigram.vector.config import VectorConfig
from lexigram.vector.exceptions import VectorError as VectorStoreError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def config() -> VectorConfig:
    """Minimal vector config."""
    return VectorConfig(
        backend="qdrant",
        collection_name="test_collection",
        default_dimension=3,
        enable_cache=False,
    )


@pytest.fixture
def mock_infra_store():
    """Mocked infra VectorStoreProtocol."""
    store = MagicMock()
    store.collection_exists = AsyncMock(return_value=True)
    store.create_collection = AsyncMock()
    store.get_collection = AsyncMock()
    store.health_check = AsyncMock()
    return store


@pytest.fixture
def mock_collection():
    """Mocked infra VectorCollectionProtocol."""
    col = MagicMock()
    col.upsert = AsyncMock(return_value=UpsertResult(upserted_count=1))
    col.search = AsyncMock(return_value=[])
    col.delete = AsyncMock(return_value=DeleteResult(deleted_count=2))
    col.count = AsyncMock(return_value=5)
    return col


@pytest.fixture
def adapter_with_collection(config, mock_infra_store, mock_collection) -> VectorStoreAdapter:
    """Adapter already wired to a collection (short-circuits _ensure_collection)."""
    mock_infra_store.get_collection.return_value = mock_collection
    adapter = VectorStoreAdapter(
        infra_store=mock_infra_store,
        collection_name="test_collection",
        dimension=3,
        config=config,
    )
    # Pre-populate the lazy collection so _ensure_collection does not hit the store.
    adapter._collection = mock_collection
    return adapter


# ---------------------------------------------------------------------------
# add()
# ---------------------------------------------------------------------------


class TestAdapterAdd:
    @pytest.mark.asyncio
    async def test_add_with_precomputed_embeddings_calls_upsert(
        self, adapter_with_collection, mock_collection
    ):
        """Documents with embeddings are converted to VectorRecord and upserted."""
        docs = [
            Document(id="d1", text="Hello", embedding=[0.1, 0.2, 0.3]),
        ]

        result = await adapter_with_collection.add(docs)

        assert result.is_ok()
        assert result.unwrap() == ["d1"]
        mock_collection.upsert.assert_awaited_once()
        records: list[VectorRecord] = mock_collection.upsert.call_args[0][0]
        assert records[0].id == "d1"
        assert records[0].vector == [0.1, 0.2, 0.3]
        assert records[0].content == "Hello"

    @pytest.mark.asyncio
    async def test_add_auto_generates_id_when_missing(
        self, adapter_with_collection, mock_collection
    ):
        """Documents without IDs get auto-generated UUIDs."""
        docs = [Document(text="No ID", embedding=[1.0, 0.0, 0.0])]

        result = await adapter_with_collection.add(docs)

        assert result.is_ok()
        ids = result.unwrap()
        assert len(ids) == 1
        assert len(ids[0]) > 0  # non-empty UUID string

    @pytest.mark.asyncio
    async def test_add_without_embedding_and_no_fn_returns_err(
        self, adapter_with_collection
    ):
        """add() returns Err when a document has no embedding and embedding_fn is absent."""
        docs = [Document(id="x", text="Needs embedding")]  # no embedding set

        result = await adapter_with_collection.add(docs)

        assert result.is_err()
        assert isinstance(result.unwrap_err(), VectorStoreError)

    @pytest.mark.asyncio
    async def test_add_calls_embedding_fn_when_no_doc_embedding(
        self, config, mock_infra_store, mock_collection
    ):
        """add() uses embedding_fn to generate missing embeddings."""
        mock_infra_store.collection_exists.return_value = True
        mock_infra_store.get_collection.return_value = mock_collection

        embedding_fn = AsyncMock(return_value=[[0.5, 0.6, 0.7]])

        adapter = VectorStoreAdapter(
            infra_store=mock_infra_store,
            collection_name="test_collection",
            dimension=3,
            config=config,
            embedding_fn=embedding_fn,
        )
        adapter._collection = mock_collection

        docs = [Document(id="e1", text="Needs embedding")]

        result = await adapter.add(docs)

        assert result.is_ok()
        embedding_fn.assert_awaited_once_with(["Needs embedding"])
        records: list[VectorRecord] = mock_collection.upsert.call_args[0][0]
        assert records[0].vector == [0.5, 0.6, 0.7]

    @pytest.mark.asyncio
    async def test_add_collection_init_error_returns_err(self, config, mock_infra_store):
        """add() returns Err when _ensure_collection raises ConnectionError."""
        mock_infra_store.collection_exists = AsyncMock(
            side_effect=ConnectionError("unreachable")
        )
        adapter = VectorStoreAdapter(
            infra_store=mock_infra_store,
            collection_name="test_collection",
            dimension=3,
            config=config,
        )

        result = await adapter.add([Document(id="x", text="t", embedding=[1.0, 0.0, 0.0])])

        assert result.is_err()
        assert "Collection initialisation failed" in str(result.unwrap_err())


# ---------------------------------------------------------------------------
# batch_upsert()
# ---------------------------------------------------------------------------


class TestAdapterBatchUpsert:
    @pytest.mark.asyncio
    async def test_batch_upsert_processes_all_docs(
        self, adapter_with_collection, mock_collection
    ):
        """batch_upsert() returns total upserted count across all batches."""
        docs = [
            Document(id=f"d{i}", text=f"doc {i}", embedding=[float(i), 0.0, 0.0])
            for i in range(5)
        ]

        result = await adapter_with_collection.batch_upsert(docs, batch_size=2)

        assert result.is_ok()
        assert result.unwrap() == 5

    @pytest.mark.asyncio
    async def test_batch_upsert_propagates_err(self, config, mock_infra_store):
        """batch_upsert() propagates Err from a failing batch."""
        failing_collection = MagicMock()
        failing_collection.upsert = AsyncMock(side_effect=ValueError("upsert boom"))

        mock_infra_store.collection_exists.return_value = True
        mock_infra_store.get_collection.return_value = failing_collection

        adapter = VectorStoreAdapter(
            infra_store=mock_infra_store,
            collection_name="test_collection",
            dimension=3,
            config=config,
        )
        adapter._collection = failing_collection

        docs = [Document(id="x", text="t", embedding=[1.0, 0.0, 0.0])]
        result = await adapter.batch_upsert(docs)

        assert result.is_err()


# ---------------------------------------------------------------------------
# search()
# ---------------------------------------------------------------------------


class TestAdapterSearch:
    @pytest.mark.asyncio
    async def test_search_converts_infra_results(
        self, adapter_with_collection, mock_collection
    ):
        """search() maps infra SearchResult objects to AI SearchResult objects."""
        infra_hits = [
            InfraSearchResult(id="r1", score=0.9, content="doc text", metadata={"k": "v"}),
            InfraSearchResult(id="r2", score=0.7, content="other", metadata={}),
        ]
        mock_collection.search.return_value = infra_hits

        result = await adapter_with_collection.search([0.1, 0.2, 0.3], top_k=2)

        assert result.is_ok()
        hits: list[RAGSearchResult] = result.unwrap()
        assert len(hits) == 2
        assert hits[0].score == 0.9
        assert hits[0].document.id == "r1"
        assert hits[0].document.text == "doc text"
        assert hits[0].document.metadata == {"k": "v"}
        assert hits[0].rank == 0
        assert hits[1].rank == 1

    @pytest.mark.asyncio
    async def test_search_empty_returns_ok_empty_list(
        self, adapter_with_collection, mock_collection
    ):
        """search() with no hits returns Ok([])."""
        mock_collection.search.return_value = []

        result = await adapter_with_collection.search([0.0, 0.0, 0.0])

        assert result.is_ok()
        assert result.unwrap() == []

    @pytest.mark.asyncio
    async def test_search_passes_score_threshold(
        self, adapter_with_collection, mock_collection
    ):
        """search() passes min_score to the infra SearchQuery."""
        from lexigram.contracts.data.vector.types import SearchQuery

        mock_collection.search.return_value = []

        await adapter_with_collection.search(
            [1.0, 0.0, 0.0], top_k=5, score_threshold=0.75
        )

        call_arg: SearchQuery = mock_collection.search.call_args[0][0]
        assert call_arg.min_score == 0.75
        assert call_arg.top_k == 5

    @pytest.mark.asyncio
    async def test_search_with_filters_builds_metadata_filter(
        self, adapter_with_collection, mock_collection
    ):
        """search() converts dict filters to infra MetadataFilter."""
        from lexigram.contracts.data.vector.types import SearchQuery

        mock_collection.search.return_value = []

        await adapter_with_collection.search(
            [1.0, 0.0, 0.0], filters={"source": "wiki"}
        )

        call_arg: SearchQuery = mock_collection.search.call_args[0][0]
        assert call_arg.filter is not None

    @pytest.mark.asyncio
    async def test_search_collection_error_returns_err(
        self, adapter_with_collection, mock_collection
    ):
        """search() returns Err when the infra collection raises."""
        mock_collection.search = AsyncMock(side_effect=RuntimeError("backend down"))

        result = await adapter_with_collection.search([0.0, 0.1, 0.2])

        assert result.is_err()
        assert "Search failed" in str(result.unwrap_err())


# ---------------------------------------------------------------------------
# search_text()
# ---------------------------------------------------------------------------


class TestAdapterSearchText:
    @pytest.mark.asyncio
    async def test_search_text_requires_embedding_fn(self, adapter_with_collection):
        """search_text() returns Err when no embedding_fn is configured."""
        result = await adapter_with_collection.search_text("query")

        assert result.is_err()
        assert "search_text requires" in str(result.unwrap_err())

    @pytest.mark.asyncio
    async def test_search_text_embeds_and_searches(
        self, config, mock_infra_store, mock_collection
    ):
        """search_text() embeds the query text then delegates to search()."""
        mock_infra_store.collection_exists.return_value = True
        mock_infra_store.get_collection.return_value = mock_collection

        infra_hits = [
            InfraSearchResult(id="r1", score=0.85, content="relevant", metadata={})
        ]
        mock_collection.search.return_value = infra_hits

        embedding_fn = AsyncMock(return_value=[[0.1, 0.2, 0.3]])

        adapter = VectorStoreAdapter(
            infra_store=mock_infra_store,
            collection_name="test_collection",
            dimension=3,
            config=config,
            embedding_fn=embedding_fn,
        )
        adapter._collection = mock_collection

        result = await adapter.search_text("my query", top_k=1)

        assert result.is_ok()
        embedding_fn.assert_awaited_once_with(["my query"])
        hits = result.unwrap()
        assert len(hits) == 1
        assert hits[0].document.id == "r1"


# ---------------------------------------------------------------------------
# delete()
# ---------------------------------------------------------------------------


class TestAdapterDelete:
    @pytest.mark.asyncio
    async def test_delete_returns_deletion_count(
        self, adapter_with_collection, mock_collection
    ):
        """delete() returns Ok(deleted_count) from the infra DeleteResult."""
        mock_collection.delete.return_value = DeleteResult(deleted_count=3)

        result = await adapter_with_collection.delete(["id1", "id2", "id3"])

        assert result.is_ok()
        assert result.unwrap() == 3

    @pytest.mark.asyncio
    async def test_delete_infra_error_returns_err(
        self, adapter_with_collection, mock_collection
    ):
        """delete() returns Err when the infra collection raises."""
        mock_collection.delete = AsyncMock(side_effect=ConnectionError("timeout"))

        result = await adapter_with_collection.delete(["x"])

        assert result.is_err()
        assert "Delete failed" in str(result.unwrap_err())


# ---------------------------------------------------------------------------
# health_check()
# ---------------------------------------------------------------------------


class TestAdapterHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check_returns_healthy_with_count(
        self, adapter_with_collection, mock_collection
    ):
        """health_check() reports HEALTHY with the collection vector count."""
        mock_collection.count.return_value = 42

        result = await adapter_with_collection.health_check()

        assert result.status == HealthStatus.HEALTHY
        assert result.details["vector_count"] == 42
        assert result.details["collection"] == "test_collection"

    @pytest.mark.asyncio
    async def test_health_check_returns_unhealthy_on_error(
        self, config, mock_infra_store, mock_collection
    ):
        """health_check() reports UNHEALTHY when the collection raises."""
        mock_collection.count = AsyncMock(side_effect=ConnectionError("down"))
        mock_infra_store.collection_exists.return_value = True
        mock_infra_store.get_collection.return_value = mock_collection

        adapter = VectorStoreAdapter(
            infra_store=mock_infra_store,
            collection_name="test_collection",
            dimension=3,
            config=config,
        )
        adapter._collection = mock_collection

        result = await adapter.health_check()

        assert result.status == HealthStatus.UNHEALTHY
        assert result.error is not None
