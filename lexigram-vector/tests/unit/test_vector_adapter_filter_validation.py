"""Adapter-boundary security tests for vector metadata filters."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.data.vector.filters import (
    FilterOperator,
    LogicalOperator,
    MetadataConditionGroup,
)
from lexigram.contracts.data.vector.types import DeleteResult, UpsertResult
from lexigram.vector.adapters.vector_store import VectorStoreAdapter
from lexigram.vector.config import VectorConfig


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
def adapter_with_collection(
    config, mock_infra_store, mock_collection
) -> VectorStoreAdapter:
    """Adapter already wired to a collection (short-circuits _ensure_collection)."""
    mock_infra_store.get_collection.return_value = mock_collection
    adapter = VectorStoreAdapter(
        infra_store=mock_infra_store,
        collection_name="test_collection",
        dimension=3,
        config=config,
    )
    adapter._collection = mock_collection
    return adapter


class TestAdapterFilterValidation:
    def test_build_filter_rejects_injection_key(self, adapter_with_collection) -> None:
        with pytest.raises(ValueError, match="Invalid metadata field name"):
            adapter_with_collection._build_filter({"x' OR 1=1--": 1})

    def test_build_filter_preserves_valid_multi_key_shape(
        self, adapter_with_collection
    ) -> None:
        group = adapter_with_collection._build_filter(
            {"source": "wiki", "status": "active"}
        )
        assert isinstance(group, MetadataConditionGroup)
        assert group.logical_operator == LogicalOperator.AND
        assert len(group.conditions) == 2
        assert {c.field for c in group.conditions} == {"source", "status"}
        assert all(c.operator == FilterOperator.EQ for c in group.conditions)

    @pytest.mark.asyncio
    async def test_search_returns_err_and_never_touches_collection(
        self, adapter_with_collection, mock_collection
    ) -> None:
        result = await adapter_with_collection.search(
            [1.0, 0.0, 0.0], filters={"x' OR 1=1--": 1}
        )
        assert result.is_err()
        mock_collection.search.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_search_valid_filter_unchanged(
        self, adapter_with_collection, mock_collection
    ) -> None:
        result = await adapter_with_collection.search(
            [1.0, 0.0, 0.0], filters={"source": "wiki"}
        )
        assert result.is_ok()
        mock_collection.search.assert_awaited_once()
