"""Tests for lexigram-vector types."""

from __future__ import annotations

import pytest

from lexigram.vector.types import BatchProgress, CollectionState, Embedding


class TestCollectionState:
    def test_default_values(self) -> None:
        state = CollectionState(
            name="test",
            dimension=128,
            distance_metric="cosine",
            index_type="hnsw",
        )
        assert state.name == "test"
        assert state.dimension == 128
        assert state.distance_metric == "cosine"
        assert state.index_type == "hnsw"
        assert state.vector_count == 0
        assert state.metadata == {}

    def test_custom_metadata(self) -> None:
        state = CollectionState(
            name="test",
            dimension=128,
            distance_metric="cosine",
            index_type="hnsw",
            metadata={"key": "value"},
        )
        assert state.metadata == {"key": "value"}


class TestBatchProgress:
    def test_default_values(self) -> None:
        progress = BatchProgress(total=100, completed=50, failed=10)
        assert progress.total == 100
        assert progress.completed == 50
        assert progress.failed == 10
        assert progress.errors == []

    def test_success_rate_with_items(self) -> None:
        progress = BatchProgress(total=100, completed=80, failed=20)
        assert progress.success_rate == 0.8

    def test_success_rate_with_zero_total(self) -> None:
        progress = BatchProgress(total=0, completed=0, failed=0)
        assert progress.success_rate == 1.0

    def test_errors_list(self) -> None:
        progress = BatchProgress(
            total=100, completed=90, failed=10, errors=["error1", "error2"]
        )
        assert progress.errors == ["error1", "error2"]


class TestEmbedding:
    def test_create_embedding(self) -> None:
        embedding = Embedding(vector=[0.1, 0.2, 0.3], model="text-embedding-3", dimension=3)
        assert embedding.vector == [0.1, 0.2, 0.3]
        assert embedding.model == "text-embedding-3"
        assert embedding.dimension == 3

    def test_empty_vector(self) -> None:
        embedding = Embedding(vector=[], model="test", dimension=0)
        assert embedding.vector == []
        assert embedding.dimension == 0