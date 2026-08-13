"""Unit tests for ChromaStore and ChromaCollection."""

from __future__ import annotations

import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Stub chromadb before importing the backend so lazy `import chromadb`
# inside connect() resolves without the real package installed.
# ---------------------------------------------------------------------------

_chromadb_stub = MagicMock()
_chroma_collection_stub = MagicMock()
_chromadb_stub.HttpClient = MagicMock()
_chromadb_stub.EphemeralClient = MagicMock()
_chromadb_stub.Settings = MagicMock(return_value=MagicMock())

sys.modules.setdefault("chromadb", _chromadb_stub)

from lexigram.contracts.core.health import HealthStatus  # noqa: E402
from lexigram.contracts.data.vector import (  # noqa: E402
    CollectionConfig,
    DistanceMetric,
    SearchQuery,
    VectorRecord,
)
from lexigram.vector.backends.chroma import ChromaCollection, ChromaStore  # noqa: E402
from lexigram.vector.config import ChromaConfig  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(use_http: bool = False) -> ChromaConfig:
    return ChromaConfig(host="localhost", port=8000, use_http_client=use_http)


def _make_chroma_collection(name: str = "test") -> MagicMock:
    col = MagicMock()
    col.name = name
    col.metadata = {"hnsw:space": "cosine"}
    col.count = MagicMock(return_value=5)
    col.upsert = MagicMock()
    col.query = MagicMock(return_value={
        "ids": [["id1", "id2"]],
        "distances": [[0.1, 0.3]],
        "metadatas": [[{"key": "val"}, {}]],
        "documents": [["doc1", "doc2"]],
    })
    col.get = MagicMock(return_value={
        "ids": ["id1"],
        "embeddings": [[0.1, 0.2]],
        "metadatas": [{"key": "val"}],
        "documents": ["doc1"],
    })
    col.delete = MagicMock()
    return col


def _make_chroma_client(collection: MagicMock | None = None) -> MagicMock:
    col = collection or _make_chroma_collection()
    client = MagicMock()
    client.get_version = MagicMock(return_value="0.5.0")
    client.list_collections = MagicMock(return_value=[col])
    client.get_collection = MagicMock(return_value=col)
    client.get_or_create_collection = MagicMock(return_value=col)
    client.create_collection = MagicMock()
    client.delete_collection = MagicMock()
    return client


# ---------------------------------------------------------------------------
# ChromaStore — lifecycle
# ---------------------------------------------------------------------------


class TestChromaStoreConnect:
    @pytest.mark.asyncio
    async def test_connect_ephemeral_client(self) -> None:
        config = _make_config(use_http=False)
        store = ChromaStore(config)
        mock_client = _make_chroma_client()
        _chromadb_stub.EphemeralClient = MagicMock(return_value=mock_client)
        _chromadb_stub.HttpClient = MagicMock(return_value=mock_client)

        with patch.dict(sys.modules, {"chromadb": _chromadb_stub}):
            await store.connect()

        assert store._client is not None

    @pytest.mark.asyncio
    async def test_connect_http_client(self) -> None:
        config = _make_config(use_http=True)
        store = ChromaStore(config)
        mock_client = _make_chroma_client()
        _chromadb_stub.HttpClient = MagicMock(return_value=mock_client)

        with patch.dict(sys.modules, {"chromadb": _chromadb_stub}):
            await store.connect()

        assert store._client is not None

    @pytest.mark.asyncio
    async def test_disconnect_clears_client(self) -> None:
        config = _make_config()
        store = ChromaStore(config)
        store._client = _make_chroma_client()
        await store.disconnect()
        assert store._client is None


# ---------------------------------------------------------------------------
# ChromaStore — health_check
# ---------------------------------------------------------------------------


class TestChromaStoreHealthCheck:
    @pytest.mark.asyncio
    async def test_healthy_when_connected(self) -> None:
        config = _make_config()
        store = ChromaStore(config)
        store._client = _make_chroma_client()

        result = await store.health_check()

        assert result.status == HealthStatus.HEALTHY
        assert result.component == "chroma"
        assert result.details is not None
        assert "version" in result.details

    @pytest.mark.asyncio
    async def test_unhealthy_when_not_connected(self) -> None:
        config = _make_config()
        store = ChromaStore(config)

        result = await store.health_check()

        assert result.status == HealthStatus.UNHEALTHY
        assert result.component == "chroma"

    @pytest.mark.asyncio
    async def test_unhealthy_on_exception(self) -> None:
        config = _make_config()
        store = ChromaStore(config)
        client = _make_chroma_client()
        client.get_version = MagicMock(side_effect=OSError("Connection refused"))
        store._client = client

        result = await store.health_check()

        assert result.status == HealthStatus.UNHEALTHY
        assert result.component == "chroma"
        assert "Connection refused" in (result.message or "")


# ---------------------------------------------------------------------------
# ChromaStore — collection management
# ---------------------------------------------------------------------------


class TestChromaStoreCollections:
    @pytest.fixture
    def store(self) -> ChromaStore:
        s = ChromaStore(_make_config())
        s._client = _make_chroma_client()
        return s

    @pytest.mark.asyncio
    async def test_list_collections(self, store: ChromaStore) -> None:
        result = await store.list_collections()
        assert len(result) == 1
        assert result[0].name == "test"

    @pytest.mark.asyncio
    async def test_create_collection(self, store: ChromaStore) -> None:
        config = CollectionConfig(
            name="new-col", dimension=128, distance_metric=DistanceMetric.COSINE
        )
        await store.create_collection(config)
        store._client.create_collection.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_collection(self, store: ChromaStore) -> None:
        await store.delete_collection("test")
        store._client.delete_collection.assert_called_once_with("test")

    @pytest.mark.asyncio
    async def test_collection_exists_true(self, store: ChromaStore) -> None:
        exists = await store.collection_exists("test")
        assert exists is True

    @pytest.mark.asyncio
    async def test_collection_exists_false(self, store: ChromaStore) -> None:
        store._client.get_collection = MagicMock(side_effect=Exception("Not found"))
        exists = await store.collection_exists("missing")
        assert exists is False

    @pytest.mark.asyncio
    async def test_get_collection_returns_chroma_collection(
        self, store: ChromaStore
    ) -> None:
        col = await store.get_collection("test")
        assert isinstance(col, ChromaCollection)
        assert col.name == "test"

    @pytest.mark.asyncio
    async def test_get_or_create_collection(self, store: ChromaStore) -> None:
        config = CollectionConfig(
            name="test", dimension=64, distance_metric=DistanceMetric.COSINE
        )
        col = await store.get_or_create_collection(config)
        assert isinstance(col, ChromaCollection)
        store._client.get_or_create_collection.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_when_not_connected(self) -> None:
        store = ChromaStore(_make_config())
        with pytest.raises(RuntimeError, match="Not connected"):
            await store.list_collections()


# ---------------------------------------------------------------------------
# ChromaCollection — upsert
# ---------------------------------------------------------------------------


class TestChromaCollectionUpsert:
    @pytest.fixture
    def col(self) -> ChromaCollection:
        return ChromaCollection(
            collection=_make_chroma_collection(),
            name="test",
            dimension=3,
            distance_metric=DistanceMetric.COSINE,
        )

    @pytest.mark.asyncio
    async def test_upsert_returns_count(self, col: ChromaCollection) -> None:
        records = [
            VectorRecord(id="1", vector=[0.1, 0.2, 0.3], metadata={}),
            VectorRecord(id="2", vector=[0.4, 0.5, 0.6], metadata={}),
        ]
        result = await col.upsert(records)
        assert result.upserted_count == 2

    @pytest.mark.asyncio
    async def test_upsert_empty_returns_zero(self, col: ChromaCollection) -> None:
        result = await col.upsert([])
        assert result.upserted_count == 0
        col._collection.upsert.assert_not_called()

    @pytest.mark.asyncio
    async def test_upsert_calls_chroma_upsert(self, col: ChromaCollection) -> None:
        records = [VectorRecord(id="1", vector=[0.1], metadata={"k": "v"}, content="hello")]
        await col.upsert(records)
        col._collection.upsert.assert_called_once()
        kwargs = col._collection.upsert.call_args[1]
        assert kwargs["ids"] == ["1"]
        assert kwargs["documents"] == ["hello"]


# ---------------------------------------------------------------------------
# ChromaCollection — search
# ---------------------------------------------------------------------------


class TestChromaCollectionSearch:
    @pytest.fixture
    def col(self) -> ChromaCollection:
        return ChromaCollection(
            collection=_make_chroma_collection(),
            name="test",
            dimension=3,
            distance_metric=DistanceMetric.COSINE,
        )

    @pytest.mark.asyncio
    async def test_search_returns_results(self, col: ChromaCollection) -> None:
        query = SearchQuery(vector=[0.1, 0.2, 0.3], top_k=5)
        results = await col.search(query)
        assert len(results) == 2
        assert results[0].id == "id1"
        assert results[0].score == pytest.approx(0.9)

    @pytest.mark.asyncio
    async def test_search_empty_results(self, col: ChromaCollection) -> None:
        col._collection.query = MagicMock(return_value={"ids": [[]], "distances": [[]], "metadatas": [[]], "documents": [[]]})
        query = SearchQuery(vector=[0.1], top_k=5)
        results = await col.search(query)
        assert results == []

    @pytest.mark.asyncio
    async def test_search_min_score_filters(self, col: ChromaCollection) -> None:
        # distances 0.1 → score 0.9, 0.3 → score 0.7; min_score=0.8 should keep only first
        query = SearchQuery(vector=[0.1, 0.2, 0.3], top_k=5, min_score=0.8)
        results = await col.search(query)
        assert len(results) == 1
        assert results[0].id == "id1"


# ---------------------------------------------------------------------------
# ChromaCollection — get, delete, count
# ---------------------------------------------------------------------------


class TestChromaCollectionOps:
    @pytest.fixture
    def col(self) -> ChromaCollection:
        return ChromaCollection(
            collection=_make_chroma_collection(),
            name="test",
            dimension=3,
            distance_metric=DistanceMetric.COSINE,
        )

    @pytest.mark.asyncio
    async def test_get_returns_records(self, col: ChromaCollection) -> None:
        records = await col.get(["id1"])
        assert len(records) == 1
        assert records[0].id == "id1"
        assert records[0].content == "doc1"

    @pytest.mark.asyncio
    async def test_delete_returns_count(self, col: ChromaCollection) -> None:
        result = await col.delete(["id1", "id2"])
        assert result.deleted_count == 2
        col._collection.delete.assert_called_once_with(ids=["id1", "id2"])

    @pytest.mark.asyncio
    async def test_count_returns_value(self, col: ChromaCollection) -> None:
        count = await col.count()
        assert count == 5

    @pytest.mark.asyncio
    async def test_delete_by_filter(self, col: ChromaCollection) -> None:
        await col.delete_by_filter({"key": "val"})
        col._collection.delete.assert_called_once_with(where={"key": "val"})


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------



class TestChromaCollectionUpdateMetadata:
    @pytest.fixture
    def col(self) -> ChromaCollection:
        return ChromaCollection(
            collection=_make_chroma_collection(),
            name="test",
            dimension=3,
            distance_metric=DistanceMetric.COSINE,
        )

    @pytest.mark.asyncio
    async def test_update_metadata_existing_record(self, col: ChromaCollection) -> None:
        col._collection.get.return_value = {
            "ids": ["vec1"],
            "metadatas": [{"key": "old"}],
        }
        col._collection.update.return_value = None
        result = await col.update_metadata("vec1", {"new_key": "val"})
        assert result is True
        col._collection.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_metadata_merges_with_existing(self, col: ChromaCollection) -> None:
        col._collection.get.return_value = {
            "ids": ["vec1"],
            "metadatas": [{"existing": "value"}],
        }
        col._collection.update.return_value = None
        await col.update_metadata("vec1", {"new_key": "new_val"})
        call_kwargs = col._collection.update.call_args[1]
        merged = call_kwargs["metadatas"][0]
        assert "existing" in merged
        assert "new_key" in merged

    @pytest.mark.asyncio
    async def test_update_metadata_nonexistent_record_returns_false(self, col: ChromaCollection) -> None:
        col._collection.get.return_value = {"ids": [], "metadatas": []}
        result = await col.update_metadata("nonexistent", {"k": "v"})
        assert result is False

    @pytest.mark.asyncio
    async def test_update_metadata_error_returns_false(self, col: ChromaCollection) -> None:
        col._collection.get.side_effect = RuntimeError("chroma error")
        result = await col.update_metadata("vec1", {"k": "v"})
        assert result is False

class TestExports:
    def test_chroma_store_importable_from_backends(self) -> None:
        from lexigram.vector.backends import ChromaStore as CS
        assert CS is ChromaStore

    def test_chroma_config_importable_from_vector(self) -> None:
        from lexigram.vector.config import ChromaConfig as CC
        assert CC is ChromaConfig
