"""Unit tests for WeaviateStore and WeaviateCollection."""

from __future__ import annotations

import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Stub weaviate before importing the backend so lazy `import weaviate` inside
# connect() and other methods resolves without the real package installed.
# ---------------------------------------------------------------------------

_weaviate_stub = MagicMock()
_weaviate_auth_stub = MagicMock()
_weaviate_connect_stub = MagicMock()
_weaviate_classes_config_stub = MagicMock()
_weaviate_classes_data_stub = MagicMock()
_weaviate_classes_query_stub = MagicMock()

# Ensure v4 API path: hasattr(weaviate, "WeaviateAsyncClient") → True
_weaviate_stub.WeaviateAsyncClient = MagicMock()
_weaviate_stub.auth = _weaviate_auth_stub
_weaviate_stub.connect = _weaviate_connect_stub
_weaviate_stub.classes = MagicMock()
_weaviate_stub.classes.config = _weaviate_classes_config_stub
_weaviate_stub.classes.data = _weaviate_classes_data_stub
_weaviate_stub.classes.query = _weaviate_classes_query_stub

sys.modules.setdefault("weaviate", _weaviate_stub)
sys.modules.setdefault("weaviate.auth", _weaviate_auth_stub)
sys.modules.setdefault("weaviate.connect", _weaviate_connect_stub)
sys.modules.setdefault("weaviate.classes", MagicMock())
sys.modules.setdefault("weaviate.classes.config", _weaviate_classes_config_stub)
sys.modules.setdefault("weaviate.classes.data", _weaviate_classes_data_stub)
sys.modules.setdefault("weaviate.classes.query", _weaviate_classes_query_stub)

from lexigram.contracts.core.health import HealthStatus  # noqa: E402
from lexigram.contracts.data.vector import (  # noqa: E402
    CollectionConfig,
    DistanceMetric,
    SearchQuery,
    VectorRecord,
)
from lexigram.vector.backends.weaviate import (  # noqa: E402
    WeaviateCollection,
    WeaviateStore,
)
from lexigram.vector.config import WeaviateConfig  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config() -> WeaviateConfig:
    return WeaviateConfig(url="http://localhost:8080")


def _make_collections_mock() -> MagicMock:
    cols = MagicMock()
    col_meta = MagicMock()
    col_meta.vector_config = {}
    cols.list_all = AsyncMock(return_value={"test": col_meta})
    cols.create = AsyncMock()
    cols.delete = AsyncMock()
    cols.exists = AsyncMock(return_value=True)
    cols.get = MagicMock(return_value=MagicMock())
    return cols


def _make_weaviate_client() -> MagicMock:
    client = MagicMock()
    client.connect = AsyncMock()
    client.close = AsyncMock()
    client.is_ready = AsyncMock(return_value=True)
    client.collections = _make_collections_mock()
    return client


def _make_raw_collection() -> MagicMock:
    col = MagicMock()

    # data sub-object
    col.data = MagicMock()
    response = MagicMock()
    response.errors = {}
    col.data.insert_many = AsyncMock(return_value=response)
    col.data.get_by_id = AsyncMock(return_value=None)
    col.data.delete_by_id = AsyncMock()
    col.data.delete_many = AsyncMock()
    col.data.update = AsyncMock()

    # query sub-object
    col.query = MagicMock()
    col.query.near_vector = AsyncMock(return_value=MagicMock(objects=[]))

    # aggregate sub-object
    col.aggregate = MagicMock()
    col.aggregate.over_all = AsyncMock(return_value=MagicMock(total_count=0))

    return col


def _make_weaviate_obj(
    uuid: str, props: dict[str, Any], distance: float = 0.1
) -> MagicMock:
    obj = MagicMock()
    obj.uuid = uuid
    obj.properties = props
    obj.vector = [0.1, 0.2, 0.3]
    obj.metadata = MagicMock()
    obj.metadata.distance = distance
    return obj


# ---------------------------------------------------------------------------
# WeaviateStore — lifecycle
# ---------------------------------------------------------------------------


class TestWeaviateStoreConnect:
    @pytest.mark.asyncio
    async def test_connect_creates_client(self) -> None:
        config = _make_config()
        store = WeaviateStore(config)
        mock_client = _make_weaviate_client()

        conn_params_mock = MagicMock()
        _weaviate_connect_stub.ConnectionParams = MagicMock()
        _weaviate_connect_stub.ConnectionParams.from_url = MagicMock(
            return_value=conn_params_mock
        )
        _weaviate_stub.WeaviateAsyncClient = MagicMock(return_value=mock_client)

        import sys

        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(
            sys.modules,
            {
                "weaviate": _weaviate_stub,
                "weaviate.connect": _weaviate_connect_stub,
            },
        ):
            await store.connect()

        assert store._client is not None

    @pytest.mark.asyncio
    async def test_disconnect_cleans_up(self) -> None:
        store = WeaviateStore(_make_config())
        store._client = _make_weaviate_client()
        await store.disconnect()
        assert store._client is None

    @pytest.mark.asyncio
    async def test_disconnect_noop_when_not_connected(self) -> None:
        store = WeaviateStore(_make_config())
        # Should not raise
        await store.disconnect()
        assert store._client is None


# ---------------------------------------------------------------------------
# WeaviateStore — health_check
# ---------------------------------------------------------------------------


class TestWeaviateStoreHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check_healthy(self) -> None:
        store = WeaviateStore(_make_config())
        store._client = _make_weaviate_client()

        result = await store.health_check()

        assert result.status == HealthStatus.HEALTHY
        assert result.component == "weaviate"

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self) -> None:
        store = WeaviateStore(_make_config())
        # No client → unhealthy
        result = await store.health_check()

        assert result.status == HealthStatus.UNHEALTHY
        assert result.component == "weaviate"

    @pytest.mark.asyncio
    async def test_health_check_unhealthy_on_exception(self) -> None:
        store = WeaviateStore(_make_config())
        client = _make_weaviate_client()
        client.is_ready = AsyncMock(side_effect=OSError("timeout"))
        store._client = client

        result = await store.health_check()

        assert result.status == HealthStatus.UNHEALTHY
        assert "timeout" in (result.message or "")


# ---------------------------------------------------------------------------
# WeaviateStore — collection management
# ---------------------------------------------------------------------------


class TestWeaviateStoreCollections:
    @pytest.fixture
    def store(self) -> WeaviateStore:
        s = WeaviateStore(_make_config())
        s._client = _make_weaviate_client()
        return s

    @pytest.mark.asyncio
    async def test_list_collections(self, store: WeaviateStore) -> None:
        result = await store.list_collections()
        assert len(result) == 1
        assert result[0].name == "test"

    @pytest.mark.asyncio
    async def test_create_collection(self, store: WeaviateStore) -> None:
        config = CollectionConfig(
            name="new-col", dimension=128, distance_metric=DistanceMetric.COSINE
        )
        import sys

        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(
            sys.modules,
            {
                "weaviate.classes.config": _weaviate_classes_config_stub,
            },
        ):
            await store.create_collection(config)
        store._client.collections.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_collection(self, store: WeaviateStore) -> None:
        await store.delete_collection("test")
        store._client.collections.delete.assert_awaited_once_with("test")

    @pytest.mark.asyncio
    async def test_collection_exists_true(self, store: WeaviateStore) -> None:
        store._client.collections.exists = AsyncMock(return_value=True)
        exists = await store.collection_exists("test")
        assert exists is True

    @pytest.mark.asyncio
    async def test_collection_exists_false(self, store: WeaviateStore) -> None:
        store._client.collections.exists = AsyncMock(return_value=False)
        exists = await store.collection_exists("missing")
        assert exists is False

    @pytest.mark.asyncio
    async def test_get_collection_returns_instance(self, store: WeaviateStore) -> None:
        col = await store.get_collection("test")
        assert isinstance(col, WeaviateCollection)
        assert col.name == "test"

    @pytest.mark.asyncio
    async def test_raises_when_not_connected(self) -> None:
        store = WeaviateStore(_make_config())
        with pytest.raises(RuntimeError, match="not connected"):
            await store.list_collections()


# ---------------------------------------------------------------------------
# WeaviateCollection — upsert
# ---------------------------------------------------------------------------


class TestWeaviateCollectionUpsert:
    @pytest.fixture
    def col(self) -> WeaviateCollection:
        return WeaviateCollection(
            raw_collection=_make_raw_collection(),
            name="test",
            dimension=3,
            distance_metric=DistanceMetric.COSINE,
        )

    @pytest.mark.asyncio
    async def test_upsert_records(self, col: WeaviateCollection) -> None:
        records = [
            VectorRecord(id="1", vector=[0.1, 0.2, 0.3], metadata={}),
            VectorRecord(id="2", vector=[0.4, 0.5, 0.6], metadata={}),
        ]
        response_mock = MagicMock()
        response_mock.errors = {}
        col._col.data.insert_many = AsyncMock(return_value=response_mock)

        import sys

        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(
            sys.modules,
            {
                "weaviate.classes.data": _weaviate_classes_data_stub,
            },
        ):
            result = await col.upsert(records)

        assert result.upserted_count == 2
        col._col.data.insert_many.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_upsert_records_with_content(self, col: WeaviateCollection) -> None:
        records = [
            VectorRecord(id="1", vector=[0.1, 0.2, 0.3], metadata={}, content="hello")
        ]
        response_mock = MagicMock()
        response_mock.errors = {}
        col._col.data.insert_many = AsyncMock(return_value=response_mock)

        import sys

        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(
            sys.modules,
            {
                "weaviate.classes.data": _weaviate_classes_data_stub,
            },
        ):
            await col.upsert(records)

        col._col.data.insert_many.assert_awaited_once()


# ---------------------------------------------------------------------------
# WeaviateCollection — search
# ---------------------------------------------------------------------------


class TestWeaviateCollectionSearch:
    @pytest.fixture
    def col(self) -> WeaviateCollection:
        raw = _make_raw_collection()
        raw.query.near_vector = AsyncMock(
            return_value=MagicMock(
                objects=[
                    _make_weaviate_obj("id1", {"key": "val"}, distance=0.1),
                    _make_weaviate_obj("id2", {}, distance=0.3),
                ]
            )
        )
        return WeaviateCollection(
            raw_collection=raw,
            name="test",
            dimension=3,
            distance_metric=DistanceMetric.COSINE,
        )

    @pytest.mark.asyncio
    async def test_search_returns_results(self, col: WeaviateCollection) -> None:
        import sys

        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(
            sys.modules,
            {
                "weaviate.classes.query": _weaviate_classes_query_stub,
            },
        ):
            query = SearchQuery(vector=[0.1, 0.2, 0.3], top_k=5)
            results = await col.search(query)
        assert len(results) == 2
        assert results[0].id == "id1"
        assert results[0].score == pytest.approx(0.9)

    @pytest.mark.asyncio
    async def test_search_with_filter(self, col: WeaviateCollection) -> None:
        from unittest.mock import patch

        from lexigram.contracts.data.vector.filters import Filter

        query = SearchQuery(
            vector=[0.1, 0.2, 0.3],
            top_k=5,
            filter=Filter.eq("category", "science"),
        )
        with patch(
            "lexigram.vector.backends.weaviate.filters.WeaviateFilterCompiler"
        ) as mock_cls:
            mock_compiler = MagicMock()
            mock_compiler.compile = MagicMock(return_value=MagicMock())
            mock_cls.return_value = mock_compiler
            with __import__("unittest.mock", fromlist=["patch"]).patch.dict(
                sys.modules,
                {
                    "weaviate.classes.query": _weaviate_classes_query_stub,
                },
            ):
                results = await col.search(query)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_empty_results(self, col: WeaviateCollection) -> None:
        col._col.query.near_vector = AsyncMock(return_value=MagicMock(objects=[]))
        import sys

        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(
            sys.modules,
            {
                "weaviate.classes.query": _weaviate_classes_query_stub,
            },
        ):
            query = SearchQuery(vector=[0.1, 0.2, 0.3], top_k=5)
            results = await col.search(query)
        assert results == []


# ---------------------------------------------------------------------------
# WeaviateCollection — get, delete, count, update_metadata
# ---------------------------------------------------------------------------


class TestWeaviateCollectionOps:
    @pytest.fixture
    def col(self) -> WeaviateCollection:
        raw = _make_raw_collection()
        obj = _make_weaviate_obj("id1", {"key": "val"})
        raw.data.get_by_id = AsyncMock(return_value=obj)
        raw.aggregate.over_all = AsyncMock(return_value=MagicMock(total_count=7))
        return WeaviateCollection(
            raw_collection=raw,
            name="test",
            dimension=3,
            distance_metric=DistanceMetric.COSINE,
        )

    @pytest.mark.asyncio
    async def test_get_by_ids(self, col: WeaviateCollection) -> None:
        records = await col.get(["id1"])
        assert len(records) == 1
        assert records[0].id == "id1"

    @pytest.mark.asyncio
    async def test_delete_by_ids(self, col: WeaviateCollection) -> None:
        result = await col.delete(["id1", "id2"])
        assert result.deleted_count == 2
        assert col._col.data.delete_by_id.await_count == 2

    @pytest.mark.asyncio
    async def test_delete_by_filter(self, col: WeaviateCollection) -> None:
        from unittest.mock import patch

        from lexigram.contracts.data.vector.filters import Filter

        with patch(
            "lexigram.vector.backends.weaviate.filters.WeaviateFilterCompiler"
        ) as mock_cls:
            mock_compiler = MagicMock()
            mock_compiler.compile = MagicMock(return_value=MagicMock())
            mock_cls.return_value = mock_compiler
            result = await col.delete_by_filter(Filter.eq("category", "old"))
        assert result.deleted_count == 0
        col._col.data.delete_many.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_count(self, col: WeaviateCollection) -> None:
        count = await col.count()
        assert count == 7

    @pytest.mark.asyncio
    async def test_update_metadata(self, col: WeaviateCollection) -> None:
        result = await col.update_metadata("id1", {"new_key": "val"})
        assert result is True
        col._col.data.update.assert_awaited_once_with(
            uuid="id1",
            properties={"new_key": "val"},
        )

    @pytest.mark.asyncio
    async def test_update_metadata_returns_false_on_error(
        self, col: WeaviateCollection
    ) -> None:
        col._col.data.update = AsyncMock(side_effect=RuntimeError("not found"))
        result = await col.update_metadata("missing", {"key": "val"})
        assert result is False
