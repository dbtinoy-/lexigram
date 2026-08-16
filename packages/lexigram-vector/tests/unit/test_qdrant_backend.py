"""Unit tests for QdrantStore and QdrantCollection."""

from __future__ import annotations

import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Stub qdrant_client before importing the backend so lazy `from qdrant_client`
# inside connect() and other methods resolves without the real package.
# ---------------------------------------------------------------------------

_qdrant_stub = MagicMock()
_qdrant_models_stub = MagicMock()
_qdrant_http_stub = MagicMock()
_qdrant_http_stub.models = _qdrant_models_stub

_qdrant_stub.AsyncQdrantClient = MagicMock()
_qdrant_stub.http = _qdrant_http_stub

sys.modules.setdefault("qdrant_client", _qdrant_stub)
sys.modules.setdefault("qdrant_client.http", _qdrant_http_stub)
sys.modules.setdefault("qdrant_client.http.models", _qdrant_models_stub)

from lexigram.contracts.core.health import HealthStatus  # noqa: E402
from lexigram.contracts.data.vector import (  # noqa: E402
    CollectionConfig,
    DistanceMetric,
    SearchQuery,
    VectorRecord,
)
from lexigram.vector.backends.qdrant import QdrantCollection, QdrantStore  # noqa: E402
from lexigram.vector.config import QdrantConfig  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config() -> QdrantConfig:
    return QdrantConfig(url="http://localhost:6333", prefer_grpc=False)


def _make_async_client() -> MagicMock:
    client = MagicMock()

    # Lifecycle
    client.close = AsyncMock()

    # Collections list
    col_desc = MagicMock()
    col_desc.name = "test"
    collections_res = MagicMock()
    collections_res.collections = [col_desc]
    client.get_collections = AsyncMock(return_value=collections_res)

    # Collection info
    info = MagicMock()
    info.config.params.vectors.size = 3
    info.config.params.vectors.distance = "Cosine"
    info.vectors_count = 10
    info.status = "green"
    client.get_collection = AsyncMock(return_value=info)

    # CRUD operations
    client.create_collection = AsyncMock()
    client.create_payload_index = AsyncMock()
    client.delete_collection = AsyncMock()
    client.collection_exists = AsyncMock(return_value=True)
    client.upsert = AsyncMock()
    client.search = AsyncMock(return_value=[])
    client.retrieve = AsyncMock(return_value=[])
    client.delete = AsyncMock()
    client.set_payload = AsyncMock()

    return client


def _make_scored_point(
    id_: str, score: float, payload: dict[str, Any] | None = None
) -> MagicMock:
    pt = MagicMock()
    pt.id = id_
    pt.score = score
    pt.payload = payload or {}
    pt.vector = [0.1, 0.2, 0.3]
    return pt


def _make_retrieved_point(
    id_: str, vector: list[float], payload: dict[str, Any] | None = None
) -> MagicMock:
    pt = MagicMock()
    pt.id = id_
    pt.vector = vector
    pt.payload = payload or {}
    return pt


# ---------------------------------------------------------------------------
# QdrantStore — lifecycle
# ---------------------------------------------------------------------------


class TestQdrantStoreConnect:
    @pytest.mark.asyncio
    async def test_connect_creates_client(self) -> None:
        config = _make_config()
        store = QdrantStore(config)
        mock_client = _make_async_client()
        _qdrant_stub.AsyncQdrantClient = MagicMock(return_value=mock_client)

        with patch.dict(sys.modules, {"qdrant_client": _qdrant_stub}):
            await store.connect()

        assert store._client is not None

    @pytest.mark.asyncio
    async def test_disconnect_cleans_up(self) -> None:
        store = QdrantStore(_make_config())
        mock_client = _make_async_client()
        store._client = mock_client
        await store.disconnect()
        assert store._client is None
        mock_client.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_disconnect_noop_when_not_connected(self) -> None:
        store = QdrantStore(_make_config())
        # Should not raise when already disconnected
        await store.disconnect()
        assert store._client is None


# ---------------------------------------------------------------------------
# QdrantStore — health_check
# ---------------------------------------------------------------------------


class TestQdrantStoreHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check_healthy(self) -> None:
        store = QdrantStore(_make_config())
        store._client = _make_async_client()

        result = await store.health_check()

        assert result.status == HealthStatus.HEALTHY
        assert result.component == "qdrant"

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self) -> None:
        store = QdrantStore(_make_config())
        # No client set → unhealthy
        result = await store.health_check()

        assert result.status == HealthStatus.UNHEALTHY
        assert result.component == "qdrant"


# ---------------------------------------------------------------------------
# QdrantStore — collection management
# ---------------------------------------------------------------------------


class TestQdrantStoreCollections:
    @pytest.fixture
    def store(self) -> QdrantStore:
        s = QdrantStore(_make_config())
        s._client = _make_async_client()
        return s

    @pytest.mark.asyncio
    async def test_list_collections(self, store: QdrantStore) -> None:
        result = await store.list_collections()
        assert len(result) == 1
        assert result[0].name == "test"

    @pytest.mark.asyncio
    async def test_create_collection(self, store: QdrantStore) -> None:
        config = CollectionConfig(
            name="new-col", dimension=128, distance_metric=DistanceMetric.COSINE
        )
        with patch.dict(
            sys.modules, {"qdrant_client.http.models": _qdrant_models_stub}
        ):
            await store.create_collection(config)
        store._client.create_collection.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_collection(self, store: QdrantStore) -> None:
        await store.delete_collection("test")
        store._client.delete_collection.assert_awaited_once_with("test")

    @pytest.mark.asyncio
    async def test_collection_exists_true(self, store: QdrantStore) -> None:
        store._client.collection_exists = AsyncMock(return_value=True)
        exists = await store.collection_exists("test")
        assert exists is True

    @pytest.mark.asyncio
    async def test_collection_exists_false(self, store: QdrantStore) -> None:
        store._client.collection_exists = AsyncMock(return_value=False)
        exists = await store.collection_exists("missing")
        assert exists is False

    @pytest.mark.asyncio
    async def test_get_collection_returns_instance(self, store: QdrantStore) -> None:
        col = await store.get_collection("test")
        assert isinstance(col, QdrantCollection)
        assert col.name == "test"

    @pytest.mark.asyncio
    async def test_raises_when_not_connected(self) -> None:
        store = QdrantStore(_make_config())
        with pytest.raises(RuntimeError, match="Not connected"):
            await store.list_collections()


# ---------------------------------------------------------------------------
# QdrantCollection — upsert
# ---------------------------------------------------------------------------


class TestQdrantCollectionUpsert:
    @pytest.fixture
    def col(self) -> QdrantCollection:
        return QdrantCollection(
            client=_make_async_client(),
            name="test",
            dimension=3,
            distance_metric=DistanceMetric.COSINE,
        )

    @pytest.mark.asyncio
    async def test_upsert_records(self, col: QdrantCollection) -> None:
        records = [
            VectorRecord(id="1", vector=[0.1, 0.2, 0.3], metadata={}),
            VectorRecord(id="2", vector=[0.4, 0.5, 0.6], metadata={}),
        ]
        with patch.dict(
            sys.modules, {"qdrant_client.http.models": _qdrant_models_stub}
        ):
            result = await col.upsert(records)
        assert result.upserted_count == 2
        col._client.upsert.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_upsert_includes_content_in_payload(
        self, col: QdrantCollection
    ) -> None:
        records = [
            VectorRecord(id="1", vector=[0.1, 0.2, 0.3], metadata={}, content="hello")
        ]
        with patch.dict(
            sys.modules, {"qdrant_client.http.models": _qdrant_models_stub}
        ):
            await col.upsert(records)
        col._client.upsert.assert_awaited_once()


# ---------------------------------------------------------------------------
# QdrantCollection — search
# ---------------------------------------------------------------------------


class TestQdrantCollectionSearch:
    @pytest.fixture
    def col(self) -> QdrantCollection:
        client = _make_async_client()
        client.search = AsyncMock(
            return_value=[
                _make_scored_point("id1", 0.9, {"key": "val"}),
                _make_scored_point("id2", 0.7, {}),
            ]
        )
        return QdrantCollection(
            client=client,
            name="test",
            dimension=3,
            distance_metric=DistanceMetric.COSINE,
        )

    @pytest.mark.asyncio
    async def test_search_returns_results(self, col: QdrantCollection) -> None:
        query = SearchQuery(vector=[0.1, 0.2, 0.3], top_k=5)
        results = await col.search(query)
        assert len(results) == 2
        assert results[0].id == "id1"
        assert results[0].score == pytest.approx(0.9)

    @pytest.mark.asyncio
    async def test_search_with_filter(self, col: QdrantCollection) -> None:
        from lexigram.contracts.data.vector.filters import Filter

        query = SearchQuery(
            vector=[0.1, 0.2, 0.3],
            top_k=5,
            filter=Filter.eq("category", "science"),
        )
        with patch(
            "lexigram.vector.backends.qdrant.filters.QdrantFilterCompiler"
        ) as mock_compiler_cls:
            mock_compiler = MagicMock()
            mock_compiler.compile = MagicMock(return_value=MagicMock())
            mock_compiler_cls.return_value = mock_compiler
            results = await col.search(query)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_empty_results(self, col: QdrantCollection) -> None:
        col._client.search = AsyncMock(return_value=[])
        query = SearchQuery(vector=[0.1, 0.2, 0.3], top_k=5)
        results = await col.search(query)
        assert results == []


# ---------------------------------------------------------------------------
# QdrantCollection — get, delete, count, update_metadata
# ---------------------------------------------------------------------------


class TestQdrantCollectionOps:
    @pytest.fixture
    def col(self) -> QdrantCollection:
        client = _make_async_client()
        client.retrieve = AsyncMock(
            return_value=[
                _make_retrieved_point("id1", [0.1, 0.2, 0.3], {"key": "val"}),
            ]
        )
        return QdrantCollection(
            client=client,
            name="test",
            dimension=3,
            distance_metric=DistanceMetric.COSINE,
        )

    @pytest.mark.asyncio
    async def test_get_by_ids(self, col: QdrantCollection) -> None:
        records = await col.get(["id1"])
        assert len(records) == 1
        assert records[0].id == "id1"
        assert records[0].vector == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_delete_by_ids(self, col: QdrantCollection) -> None:
        with patch.dict(
            sys.modules, {"qdrant_client.http.models": _qdrant_models_stub}
        ):
            result = await col.delete(["id1", "id2"])
        assert result.deleted_count == 2
        col._client.delete.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_by_filter(self, col: QdrantCollection) -> None:
        from lexigram.contracts.data.vector.filters import Filter

        with patch(
            "lexigram.vector.backends.qdrant.filters.QdrantFilterCompiler"
        ) as mock_compiler_cls:
            mock_compiler = MagicMock()
            mock_compiler.compile = MagicMock(return_value=MagicMock())
            mock_compiler_cls.return_value = mock_compiler
            result = await col.delete_by_filter(Filter.eq("category", "old"))
        assert result.deleted_count == 0

    @pytest.mark.asyncio
    async def test_count(self, col: QdrantCollection) -> None:
        info = MagicMock()
        info.vectors_count = 42
        col._client.get_collection = AsyncMock(return_value=info)
        count = await col.count()
        assert count == 42

    @pytest.mark.asyncio
    async def test_update_metadata(self, col: QdrantCollection) -> None:
        result = await col.update_metadata("id1", {"new_key": "val"})
        assert result is True
        col._client.set_payload.assert_awaited_once_with(
            collection_name="test",
            payload={"new_key": "val"},
            points=["id1"],
        )
