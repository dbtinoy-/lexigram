"""Tests for the in-memory vector store driver."""

from __future__ import annotations

import pytest

from lexigram.contracts.data.vector.enums import DistanceMetric
from lexigram.contracts.data.vector.filters import Filter
from lexigram.contracts.data.vector.types import (
    CollectionConfig,
    SearchQuery,
    VectorRecord,
)
from lexigram.vector.backends.memory import (
    MemoryVectorCollection as InMemoryVectorCollection,
)
from lexigram.vector.backends.memory import MemoryVectorStore as InMemoryVectorStore
from lexigram.vector.exceptions import (
    CollectionAlreadyExistsError,
    CollectionNotFoundError,
    DimensionMismatchError,
)


class TestInMemoryVectorStore:
    """Test suite for InMemoryVectorStore lifecycle."""

    async def test_create_collection(
        self,
        memory_store: InMemoryVectorStore,
    ) -> None:
        config = CollectionConfig(name="my_col", dimension=128)
        await memory_store.create_collection(config)
        assert await memory_store.collection_exists("my_col")

    async def test_create_duplicate_raises(
        self,
        memory_store: InMemoryVectorStore,
    ) -> None:
        config = CollectionConfig(name="dup", dimension=64)
        await memory_store.create_collection(config)
        with pytest.raises(CollectionAlreadyExistsError):
            await memory_store.create_collection(config)

    async def test_delete_collection(
        self,
        memory_store: InMemoryVectorStore,
    ) -> None:
        config = CollectionConfig(name="to_delete", dimension=64)
        await memory_store.create_collection(config)
        await memory_store.delete_collection("to_delete")
        assert not await memory_store.collection_exists("to_delete")

    async def test_delete_nonexistent_raises(
        self,
        memory_store: InMemoryVectorStore,
    ) -> None:
        with pytest.raises(CollectionNotFoundError):
            await memory_store.delete_collection("nonexistent")

    async def test_list_collections(
        self,
        memory_store: InMemoryVectorStore,
    ) -> None:
        await memory_store.create_collection(
            CollectionConfig(name="col1", dimension=128),
        )
        await memory_store.create_collection(
            CollectionConfig(name="col2", dimension=256),
        )
        collections = await memory_store.list_collections()
        assert len(collections) == 2
        names = {c.name for c in collections}
        assert names == {"col1", "col2"}


class TestInMemoryVectorCollection:
    """Test suite for InMemoryVectorCollection operations."""

    async def test_upsert_and_get(
        self,
        collection: InMemoryVectorCollection,
        sample_records: list[VectorRecord],
    ) -> None:
        result = await collection.upsert(sample_records)
        assert result.upserted_count == 3

        retrieved = await collection.get(["doc-1", "doc-3"])
        assert len(retrieved) == 2
        ids = {r.id for r in retrieved}
        assert ids == {"doc-1", "doc-3"}

    async def test_search_basic(
        self,
        collection: InMemoryVectorCollection,
        sample_records: list[VectorRecord],
    ) -> None:
        await collection.upsert(sample_records)
        query = SearchQuery(vector=[1.0, 0.0, 0.0], top_k=2)
        results = await collection.search(query)
        assert len(results) == 2
        assert results[0].id == "doc-1"  # Exact match first

    async def test_search_with_filter(
        self,
        collection: InMemoryVectorCollection,
        sample_records: list[VectorRecord],
    ) -> None:
        await collection.upsert(sample_records)
        query = SearchQuery(
            vector=[1.0, 0.0, 0.0],
            top_k=10,
            filter=Filter.eq("category", "science"),
        )
        results = await collection.search(query)
        assert all(r.metadata.get("category") == "science" for r in results)

    async def test_delete_by_id(
        self,
        collection: InMemoryVectorCollection,
        sample_records: list[VectorRecord],
    ) -> None:
        await collection.upsert(sample_records)
        result = await collection.delete(["doc-2"])
        assert result.deleted_count == 1

        remaining = await collection.get(["doc-1", "doc-2", "doc-3"])
        assert len(remaining) == 2

    async def test_delete_by_filter(
        self,
        collection: InMemoryVectorCollection,
        sample_records: list[VectorRecord],
    ) -> None:
        await collection.upsert(sample_records)
        result = await collection.delete_by_filter(
            Filter.eq("category", "arts"),
        )
        assert result.deleted_count == 1

    async def test_count(
        self,
        collection: InMemoryVectorCollection,
        sample_records: list[VectorRecord],
    ) -> None:
        assert await collection.count() == 0
        await collection.upsert(sample_records)
        assert await collection.count() == 3

    async def test_update_metadata(
        self,
        collection: InMemoryVectorCollection,
        sample_records: list[VectorRecord],
    ) -> None:
        await collection.upsert(sample_records)
        updated = await collection.update_metadata(
            "doc-1",
            {"new_field": "new_value"},
        )
        assert updated is True

        retrieved = await collection.get(["doc-1"])
        assert retrieved[0].metadata.get("new_field") == "new_value"

    async def test_dimension_mismatch(
        self,
        collection: InMemoryVectorCollection,
    ) -> None:
        wrong_dim = VectorRecord(id="wrong", vector=[1.0, 2.0])  # 2D in 3D
        with pytest.raises(DimensionMismatchError):
            await collection.upsert([wrong_dim])


class TestVectorRecord:
    """Test VectorRecord immutability."""

    def test_record_immutable(self) -> None:
        record = VectorRecord(
            id="test",
            vector=[1.0, 2.0],
            metadata={"key": "value"},
        )
        with pytest.raises(Exception):
            record.id = "new_id"

    def test_record_comparison(self) -> None:
        record1 = VectorRecord(id="test", vector=[1.0, 2.0])
        record2 = VectorRecord(id="test", vector=[1.0, 2.0])
        assert record1 == record2
