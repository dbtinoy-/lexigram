"""Unit tests for PgVectorStore and PgVectorCollection."""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.data.vector import (
    CollectionConfig,
    DistanceMetric,
    SearchQuery,
    VectorRecord,
)
from lexigram.vector.backends.pgvector import PgVectorCollection, PgVectorStore
from lexigram.vector.config import PgVectorConfig

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db_result(affected_rows: int = 1) -> MagicMock:
    """Return a mock that simulates UpdateResult / DeleteResult from the DB protocol."""
    res = MagicMock()
    res.affected_rows = affected_rows
    return res


def _make_provider() -> MagicMock:
    """Build a mock DatabaseProviderProtocol with all needed methods."""
    provider = MagicMock()

    provider.connect = AsyncMock()
    provider.disconnect = AsyncMock()
    provider.health_check = AsyncMock(
        return_value=HealthCheckResult(
            component="pgvector", status=HealthStatus.HEALTHY
        )
    )
    provider.execute = AsyncMock()
    provider.execute_query = AsyncMock(return_value=[])
    provider.execute_update = AsyncMock(return_value=_make_db_result(1))
    provider.execute_delete = AsyncMock(return_value=_make_db_result(1))
    provider.table_exists = AsyncMock(return_value=True)

    # scoped_context is an async context manager
    mock_conn = MagicMock()
    mock_conn.executemany = AsyncMock()

    @asynccontextmanager
    async def _scoped_ctx():  # type: ignore[return]
        yield

    provider.scoped_context = _scoped_ctx
    provider.get_scoped_connection = AsyncMock(return_value=mock_conn)

    return provider


# ---------------------------------------------------------------------------
# PgVectorStore — lifecycle
# ---------------------------------------------------------------------------


class TestPgVectorCollectionValidation:
    """Collection names are validated before SQL interpolation."""

    def test_plain_identifier_accepted(self) -> None:
        PgVectorCollection(
            provider=_make_provider(),
            name="articles_v1",
            dimension=384,
            distance_metric=DistanceMetric.COSINE,
        )

    @pytest.mark.parametrize(
        "name",
        [
            'v"1; DROP TABLE articles; --',
            "my collection",
            "my-collection",
            "1starts_with_digit",
        ],
    )
    def test_invalid_names_raise(self, name: str) -> None:
        with pytest.raises(ValueError, match="identifier"):
            PgVectorCollection(
                provider=_make_provider(),
                name=name,
                dimension=384,
                distance_metric=DistanceMetric.COSINE,
            )


class TestPgVectorStoreConnect:
    @pytest.mark.asyncio
    async def test_connect_creates_client(self) -> None:
        provider = _make_provider()
        store = PgVectorStore(provider, PgVectorConfig())

        await store.connect()

        provider.connect.assert_awaited_once()
        provider.execute.assert_awaited_once()
        assert (
            "CREATE EXTENSION IF NOT EXISTS vector" in provider.execute.call_args[0][0]
        )

    @pytest.mark.asyncio
    async def test_disconnect_cleans_up(self) -> None:
        provider = _make_provider()
        store = PgVectorStore(provider, PgVectorConfig())

        await store.disconnect()

        provider.disconnect.assert_awaited_once()


# ---------------------------------------------------------------------------
# PgVectorStore — health_check
# ---------------------------------------------------------------------------


class TestPgVectorStoreHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check_healthy(self) -> None:
        provider = _make_provider()
        store = PgVectorStore(provider, PgVectorConfig())

        result = await store.health_check()

        assert result.status == HealthStatus.HEALTHY
        assert result.component == "pgvector"

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self) -> None:
        provider = _make_provider()
        provider.health_check = AsyncMock(
            return_value=HealthCheckResult(
                component="pgvector", status=HealthStatus.UNHEALTHY
            )
        )
        store = PgVectorStore(provider, PgVectorConfig())

        result = await store.health_check()

        assert result.status == HealthStatus.UNHEALTHY


# ---------------------------------------------------------------------------
# PgVectorStore — collection management
# ---------------------------------------------------------------------------


class TestPgVectorStoreCollections:
    @pytest.fixture
    def store(self) -> PgVectorStore:
        provider = _make_provider()
        provider.execute_query = AsyncMock(return_value=[{"table_name": "items"}])
        return PgVectorStore(provider, PgVectorConfig())

    @pytest.mark.asyncio
    async def test_list_collections(self, store: PgVectorStore) -> None:
        result = await store.list_collections()
        assert len(result) == 1
        assert result[0].name == "items"

    @pytest.mark.asyncio
    async def test_create_collection(self, store: PgVectorStore) -> None:
        config = CollectionConfig(
            name="new_col", dimension=128, distance_metric=DistanceMetric.COSINE
        )
        await store.create_collection(config)
        # execute is called multiple times (CREATE TABLE, CREATE INDEX, metadata GIN index)
        assert store._provider.execute.await_count >= 2

    @pytest.mark.asyncio
    async def test_delete_collection(self, store: PgVectorStore) -> None:
        await store.delete_collection("items")
        store._provider.execute.assert_awaited_once()
        assert "DROP TABLE" in store._provider.execute.call_args[0][0]

    @pytest.mark.asyncio
    async def test_collection_exists_true(self, store: PgVectorStore) -> None:
        store._provider.table_exists = AsyncMock(return_value=True)
        exists = await store.collection_exists("items")
        assert exists is True

    @pytest.mark.asyncio
    async def test_collection_exists_false(self, store: PgVectorStore) -> None:
        store._provider.table_exists = AsyncMock(return_value=False)
        exists = await store.collection_exists("missing")
        assert exists is False

    @pytest.mark.asyncio
    async def test_get_collection_returns_instance(self, store: PgVectorStore) -> None:
        col = await store.get_collection("items")
        assert isinstance(col, PgVectorCollection)
        assert col.name == "items"


# ---------------------------------------------------------------------------
# PgVectorCollection — upsert
# ---------------------------------------------------------------------------


class TestPgVectorCollectionUpsert:
    @pytest.fixture
    def col(self) -> PgVectorCollection:
        return PgVectorCollection(
            provider=_make_provider(),
            name="items",
            dimension=3,
            distance_metric=DistanceMetric.COSINE,
        )

    @pytest.mark.asyncio
    async def test_upsert_records(self, col: PgVectorCollection) -> None:
        records = [
            VectorRecord(id="1", vector=[0.1, 0.2, 0.3], metadata={}),
            VectorRecord(id="2", vector=[0.4, 0.5, 0.6], metadata={}),
        ]
        result = await col.upsert(records)
        assert result.upserted_count == 2

    @pytest.mark.asyncio
    async def test_upsert_empty_list(self, col: PgVectorCollection) -> None:
        result = await col.upsert([])
        assert result.upserted_count == 0


# ---------------------------------------------------------------------------
# PgVectorCollection — search
# ---------------------------------------------------------------------------


class TestPgVectorCollectionSearch:
    @pytest.fixture
    def col(self) -> PgVectorCollection:
        provider = _make_provider()
        provider.execute_query = AsyncMock(
            return_value=[
                {
                    "id": "id1",
                    "score": 0.9,
                    "metadata": {"key": "val"},
                    "content": "doc1",
                },
                {"id": "id2", "score": 0.7, "metadata": {}, "content": None},
            ]
        )
        return PgVectorCollection(
            provider=provider,
            name="items",
            dimension=3,
            distance_metric=DistanceMetric.COSINE,
        )

    @pytest.mark.asyncio
    async def test_search_returns_results(self, col: PgVectorCollection) -> None:
        query = SearchQuery(vector=[0.1, 0.2, 0.3], top_k=5)
        results = await col.search(query)
        assert len(results) == 2
        assert results[0].id == "id1"
        assert results[0].score == pytest.approx(0.9)

    @pytest.mark.asyncio
    async def test_search_with_filter(self, col: PgVectorCollection) -> None:
        from unittest.mock import patch

        from lexigram.contracts.data.vector.filters import Filter

        query = SearchQuery(
            vector=[0.1, 0.2, 0.3],
            top_k=5,
            filter=Filter.eq("category", "science"),
        )
        with patch(
            "lexigram.vector.backends.pgvector.filters.PgVectorFilterCompiler"
        ) as mock_cls:
            mock_compiler = MagicMock()
            mock_compiler.compile = MagicMock(
                return_value=("metadata->>'category' = $1", ["science"])
            )
            mock_cls.return_value = mock_compiler
            results = await col.search(query)
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_empty_results(self, col: PgVectorCollection) -> None:
        col._provider.execute_query = AsyncMock(return_value=[])
        query = SearchQuery(vector=[0.1, 0.2, 0.3], top_k=5)
        results = await col.search(query)
        assert results == []


# ---------------------------------------------------------------------------
# PgVectorCollection — get, delete, count, update_metadata
# ---------------------------------------------------------------------------


class TestPgVectorCollectionOps:
    @pytest.fixture
    def col(self) -> PgVectorCollection:
        provider = _make_provider()
        provider.execute_query = AsyncMock(
            return_value=[
                {
                    "id": "id1",
                    "embedding": [0.1, 0.2, 0.3],
                    "metadata": {"key": "val"},
                    "content": "doc1",
                },
            ]
        )
        return PgVectorCollection(
            provider=provider,
            name="items",
            dimension=3,
            distance_metric=DistanceMetric.COSINE,
        )

    @pytest.mark.asyncio
    async def test_get_by_ids(self, col: PgVectorCollection) -> None:
        records = await col.get(["id1"])
        assert len(records) == 1
        assert records[0].id == "id1"

    @pytest.mark.asyncio
    async def test_delete_by_ids(self, col: PgVectorCollection) -> None:
        col._provider.execute_delete = AsyncMock(return_value=_make_db_result(2))
        result = await col.delete(["id1", "id2"])
        assert result.deleted_count == 2
        col._provider.execute_delete.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_by_filter(self, col: PgVectorCollection) -> None:
        from unittest.mock import patch

        from lexigram.contracts.data.vector.filters import Filter

        col._provider.execute_delete = AsyncMock(return_value=_make_db_result(3))
        with patch(
            "lexigram.vector.backends.pgvector.filters.PgVectorFilterCompiler"
        ) as mock_cls:
            mock_compiler = MagicMock()
            mock_compiler.compile = MagicMock(
                return_value=("metadata->>'category' = $1", ["old"])
            )
            mock_cls.return_value = mock_compiler
            result = await col.delete_by_filter(Filter.eq("category", "old"))
        assert result.deleted_count == 3

    @pytest.mark.asyncio
    async def test_count(self, col: PgVectorCollection) -> None:
        col._provider.execute_query = AsyncMock(return_value=[{"count": 42}])
        count = await col.count()
        assert count == 42

    @pytest.mark.asyncio
    async def test_update_metadata(self, col: PgVectorCollection) -> None:
        col._provider.execute_update = AsyncMock(return_value=_make_db_result(1))
        result = await col.update_metadata("id1", {"new_key": "val"})
        assert result is True
        col._provider.execute_update.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_metadata_not_found(self, col: PgVectorCollection) -> None:
        col._provider.execute_update = AsyncMock(return_value=_make_db_result(0))
        result = await col.update_metadata("nonexistent", {"key": "val"})
        assert result is False
