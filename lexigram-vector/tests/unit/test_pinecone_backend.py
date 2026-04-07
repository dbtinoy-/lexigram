"""Unit tests for PineconeStore and PineconeCollection."""

from __future__ import annotations

import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Stub pinecone before importing the backend so lazy `from pinecone` inside
# connect() and other methods resolves without the real package installed.
# ---------------------------------------------------------------------------

_pinecone_stub = MagicMock()
_serverless_spec_stub = MagicMock()

_pinecone_stub.PineconeAsyncio = MagicMock()
_pinecone_stub.ServerlessSpec = _serverless_spec_stub

sys.modules.setdefault("pinecone", _pinecone_stub)

from lexigram.contracts.core.health import HealthStatus  # noqa: E402
from lexigram.contracts.data.vector import (  # noqa: E402
    CollectionConfig,
    DistanceMetric,
    SearchQuery,
    VectorRecord,
)
from lexigram.vector.backends.pinecone import (  # noqa: E402
    PineconeCollection,
    PineconeStore,
)
from lexigram.vector.config import PineconeConfig  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config() -> PineconeConfig:
    from pydantic import SecretStr

    return PineconeConfig(api_key=SecretStr("test-key"), environment="us-east-1")


def _make_index_desc(name: str = "test", dimension: int = 3) -> MagicMock:
    desc = MagicMock()
    desc.name = name
    desc.dimension = dimension
    desc.metric = "cosine"
    desc.host = "https://test.pinecone.io"
    desc.status = MagicMock()
    desc.status.ready = True
    return desc


def _make_async_client(index_descs: list[MagicMock] | None = None) -> MagicMock:
    descs = index_descs or [_make_index_desc()]
    client = MagicMock()
    client.close = AsyncMock()
    client.list_indexes = AsyncMock(return_value=descs)
    client.describe_index = AsyncMock(return_value=descs[0])
    client.create_index = AsyncMock()
    client.delete_index = AsyncMock()

    mock_index = _make_mock_index()
    client.IndexAsyncio = MagicMock(return_value=mock_index)
    return client


def _make_mock_index() -> MagicMock:
    index = MagicMock()
    index.upsert = AsyncMock(return_value=MagicMock(upserted_count=2))
    index.query = AsyncMock(return_value=MagicMock(matches=[]))
    index.fetch = AsyncMock(return_value=MagicMock(vectors={}))
    index.delete = AsyncMock()
    index.describe_index_stats = AsyncMock(return_value=MagicMock(total_vector_count=5))
    index.update = AsyncMock()
    return index


def _make_query_match(
    id_: str,
    score: float,
    metadata: dict[str, Any] | None = None,
    values: list[float] | None = None,
) -> MagicMock:
    m = MagicMock()
    m.id = id_
    m.score = score
    m.metadata = metadata or {}
    m.values = values or [0.1, 0.2, 0.3]
    return m


# ---------------------------------------------------------------------------
# PineconeStore — lifecycle
# ---------------------------------------------------------------------------


class TestPineconeStoreConnect:
    @pytest.mark.asyncio
    async def test_connect_creates_client(self) -> None:
        config = _make_config()
        store = PineconeStore(config)
        mock_client = _make_async_client()
        _pinecone_stub.PineconeAsyncio = MagicMock(return_value=mock_client)

        import sys

        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(
            sys.modules, {"pinecone": _pinecone_stub}
        ):
            await store.connect()

        assert store._client is not None

    @pytest.mark.asyncio
    async def test_disconnect_cleans_up(self) -> None:
        store = PineconeStore(_make_config())
        mock_client = _make_async_client()
        store._client = mock_client
        await store.disconnect()
        assert store._client is None
        mock_client.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_disconnect_noop_when_not_connected(self) -> None:
        store = PineconeStore(_make_config())
        await store.disconnect()
        assert store._client is None


# ---------------------------------------------------------------------------
# PineconeStore — health_check
# ---------------------------------------------------------------------------


class TestPineconeStoreHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check_healthy(self) -> None:
        store = PineconeStore(_make_config())
        store._client = _make_async_client()

        result = await store.health_check()

        assert result.status == HealthStatus.HEALTHY
        assert result.component == "pinecone"

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self) -> None:
        store = PineconeStore(_make_config())
        result = await store.health_check()

        assert result.status == HealthStatus.UNHEALTHY
        assert result.component == "pinecone"

    @pytest.mark.asyncio
    async def test_health_check_unhealthy_on_exception(self) -> None:
        store = PineconeStore(_make_config())
        client = _make_async_client()
        client.list_indexes = AsyncMock(side_effect=OSError("Connection error"))
        store._client = client

        result = await store.health_check()

        assert result.status == HealthStatus.UNHEALTHY
        assert "Connection error" in (result.message or "")


# ---------------------------------------------------------------------------
# PineconeStore — collection management
# ---------------------------------------------------------------------------


class TestPineconeStoreCollections:
    @pytest.fixture
    def store(self) -> PineconeStore:
        s = PineconeStore(_make_config())
        s._client = _make_async_client()
        return s

    @pytest.mark.asyncio
    async def test_list_collections(self, store: PineconeStore) -> None:
        result = await store.list_collections()
        assert len(result) == 1
        assert result[0].name == "test"

    @pytest.mark.asyncio
    async def test_create_collection(self, store: PineconeStore) -> None:
        config = CollectionConfig(
            name="new-col", dimension=128, distance_metric=DistanceMetric.COSINE
        )
        import sys

        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(
            sys.modules, {"pinecone": _pinecone_stub}
        ):
            await store.create_collection(config)
        store._client.create_index.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_collection(self, store: PineconeStore) -> None:
        await store.delete_collection("test")
        store._client.delete_index.assert_awaited_once_with("test")

    @pytest.mark.asyncio
    async def test_collection_exists_true(self, store: PineconeStore) -> None:
        exists = await store.collection_exists("test")
        assert exists is True

    @pytest.mark.asyncio
    async def test_collection_exists_false(self, store: PineconeStore) -> None:
        store._client.list_indexes = AsyncMock(return_value=[])
        exists = await store.collection_exists("missing")
        assert exists is False

    @pytest.mark.asyncio
    async def test_get_collection_returns_instance(self, store: PineconeStore) -> None:
        col = await store.get_collection("test")
        assert isinstance(col, PineconeCollection)
        assert col.name == "test"

    @pytest.mark.asyncio
    async def test_raises_when_not_connected(self) -> None:
        store = PineconeStore(_make_config())
        with pytest.raises(RuntimeError, match="Not connected"):
            await store.list_collections()


# ---------------------------------------------------------------------------
# PineconeCollection — upsert
# ---------------------------------------------------------------------------


class TestPineconeCollectionUpsert:
    @pytest.fixture
    def col(self) -> PineconeCollection:
        return PineconeCollection(
            index=_make_mock_index(),
            name="test",
            dimension=3,
            distance_metric=DistanceMetric.COSINE,
        )

    @pytest.mark.asyncio
    async def test_upsert_records(self, col: PineconeCollection) -> None:
        records = [
            VectorRecord(id="1", vector=[0.1, 0.2, 0.3], metadata={}),
            VectorRecord(id="2", vector=[0.4, 0.5, 0.6], metadata={}),
        ]
        col._index.upsert = AsyncMock(return_value=MagicMock(upserted_count=2))
        result = await col.upsert(records)
        assert result.upserted_count == 2
        col._index.upsert.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_upsert_includes_content_in_metadata(
        self, col: PineconeCollection
    ) -> None:
        records = [
            VectorRecord(id="1", vector=[0.1, 0.2, 0.3], metadata={}, content="hello")
        ]
        col._index.upsert = AsyncMock(return_value=MagicMock(upserted_count=1))
        await col.upsert(records)
        call_kwargs = col._index.upsert.call_args[1]
        assert call_kwargs["vectors"][0]["metadata"]["content"] == "hello"


# ---------------------------------------------------------------------------
# PineconeCollection — search
# ---------------------------------------------------------------------------


class TestPineconeCollectionSearch:
    @pytest.fixture
    def col(self) -> PineconeCollection:
        index = _make_mock_index()
        index.query = AsyncMock(
            return_value=MagicMock(
                matches=[
                    _make_query_match("id1", 0.9, {"key": "val"}),
                    _make_query_match("id2", 0.7, {}),
                ]
            )
        )
        return PineconeCollection(
            index=index,
            name="test",
            dimension=3,
            distance_metric=DistanceMetric.COSINE,
        )

    @pytest.mark.asyncio
    async def test_search_returns_results(self, col: PineconeCollection) -> None:
        query = SearchQuery(vector=[0.1, 0.2, 0.3], top_k=5)
        results = await col.search(query)
        assert len(results) == 2
        assert results[0].id == "id1"
        assert results[0].score == pytest.approx(0.9)

    @pytest.mark.asyncio
    async def test_search_with_filter(self, col: PineconeCollection) -> None:
        from unittest.mock import patch

        from lexigram.contracts.data.vector.filters import Filter

        query = SearchQuery(
            vector=[0.1, 0.2, 0.3],
            top_k=5,
            filter=Filter.eq("category", "science"),
        )
        with patch(
            "lexigram.vector.backends.pinecone.filters.PineconeFilterCompiler"
        ) as mock_cls:
            mock_compiler = MagicMock()
            mock_compiler.compile = MagicMock(
                return_value={"category": {"$eq": "science"}}
            )
            mock_cls.return_value = mock_compiler
            results = await col.search(query)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_empty_results(self, col: PineconeCollection) -> None:
        col._index.query = AsyncMock(return_value=MagicMock(matches=[]))
        query = SearchQuery(vector=[0.1, 0.2, 0.3], top_k=5)
        results = await col.search(query)
        assert results == []


# ---------------------------------------------------------------------------
# PineconeCollection — get, delete, count, update_metadata
# ---------------------------------------------------------------------------


class TestPineconeCollectionOps:
    @pytest.fixture
    def col(self) -> PineconeCollection:
        index = _make_mock_index()
        vec_entry = MagicMock()
        vec_entry.values = [0.1, 0.2, 0.3]
        vec_entry.metadata = {"key": "val"}
        index.fetch = AsyncMock(return_value=MagicMock(vectors={"id1": vec_entry}))
        return PineconeCollection(
            index=index,
            name="test",
            dimension=3,
            distance_metric=DistanceMetric.COSINE,
        )

    @pytest.mark.asyncio
    async def test_get_by_ids(self, col: PineconeCollection) -> None:
        records = await col.get(["id1"])
        assert len(records) == 1
        assert records[0].id == "id1"
        assert records[0].vector == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_delete_by_ids(self, col: PineconeCollection) -> None:
        result = await col.delete(["id1", "id2"])
        assert result.deleted_count == 2
        col._index.delete.assert_awaited_once_with(ids=["id1", "id2"])

    @pytest.mark.asyncio
    async def test_delete_by_filter(self, col: PineconeCollection) -> None:
        result = await col.delete_by_filter({"category": "old"})
        assert result.deleted_count == 0
        col._index.delete.assert_awaited_once_with(filter={"category": "old"})

    @pytest.mark.asyncio
    async def test_count(self, col: PineconeCollection) -> None:
        col._index.describe_index_stats = AsyncMock(
            return_value=MagicMock(total_vector_count=42)
        )
        count = await col.count()
        assert count == 42

    @pytest.mark.asyncio
    async def test_update_metadata(self, col: PineconeCollection) -> None:
        result = await col.update_metadata("id1", {"new_key": "val"})
        assert result is True
        col._index.update.assert_awaited_once_with(
            id="id1", set_metadata={"new_key": "val"}
        )
