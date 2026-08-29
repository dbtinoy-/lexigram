"""Tests for the vector store registry."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from lexigram.vector.backends.registry import VectorStoreRegistry
from lexigram.vector.constants import (
    BACKEND_MEMORY,
    BACKEND_PGVECTOR,
    BACKEND_PINECONE,
    BACKEND_QDRANT,
)


def _make_config(backend: str = BACKEND_MEMORY) -> Any:
    """Create a minimal VectorConfig-like object for testing."""
    config = MagicMock()
    config.backend = backend
    config.memory = MagicMock()
    config.pinecone = MagicMock()
    config.qdrant = MagicMock()
    config.pgvector = MagicMock()
    return config


class TestVectorStoreRegistry:
    def test_empty_by_default(self) -> None:
        registry = VectorStoreRegistry()
        assert len(registry.backends()) == 0

    def test_with_defaults_registers_four_backends(self) -> None:
        registry = VectorStoreRegistry.with_defaults()
        assert BACKEND_MEMORY in registry
        assert BACKEND_PINECONE in registry
        assert BACKEND_QDRANT in registry
        assert BACKEND_PGVECTOR in registry
        assert len(registry.backends()) == 4

    def test_memory_returns_store(self) -> None:
        registry = VectorStoreRegistry.with_defaults()
        store = registry.create_store(BACKEND_MEMORY, _make_config(BACKEND_MEMORY))
        assert store is not None

    def test_pgvector_returns_none_sentinel(self) -> None:
        registry = VectorStoreRegistry.with_defaults()
        store = registry.create_store(BACKEND_PGVECTOR, _make_config(BACKEND_PGVECTOR))
        assert store is None

    def test_unknown_backend_raises_value_error(self) -> None:
        registry = VectorStoreRegistry.with_defaults()
        with pytest.raises(ValueError, match="Unknown vector backend"):
            registry.create_store("nonexistent", _make_config())

    def test_custom_backend_registration(self) -> None:
        registry = VectorStoreRegistry.with_defaults()

        def _custom(config: Any) -> Any:
            return "custom_store"

        registry.register("custom", _custom)
        assert "custom" in registry
        store = registry.create_store("custom", _make_config())
        assert store == "custom_store"

    def test_backends_returns_registered_names(self) -> None:
        registry = VectorStoreRegistry.with_defaults()
        backends = registry.backends()
        assert backends == [BACKEND_MEMORY, BACKEND_PINECONE, BACKEND_QDRANT, BACKEND_PGVECTOR]
