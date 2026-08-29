"""Tests for the graph store registry."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from lexigram.graph.backends.registry import GraphStoreRegistry
from lexigram.graph.constants import BACKEND_MEMORY, BACKEND_NEO4J


def _make_config(backend: str = BACKEND_MEMORY) -> Any:
    """Create a minimal GraphConfig-like object for testing."""
    config = MagicMock()
    config.backend = backend
    config.neo4j = MagicMock()
    return config


class TestGraphStoreRegistry:
    def test_empty_by_default(self) -> None:
        registry = GraphStoreRegistry()
        assert len(registry.backends()) == 0

    def test_with_defaults_registers_two_backends(self) -> None:
        registry = GraphStoreRegistry.with_defaults()
        assert BACKEND_NEO4J in registry
        assert BACKEND_MEMORY in registry
        assert len(registry.backends()) == 2

    def test_memory_returns_store(self) -> None:
        registry = GraphStoreRegistry.with_defaults()
        store = registry.create_store(BACKEND_MEMORY, _make_config(BACKEND_MEMORY))
        assert store is not None

    def test_unknown_backend_raises_value_error(self) -> None:
        registry = GraphStoreRegistry.with_defaults()
        with pytest.raises(ValueError, match="Unknown graph backend"):
            registry.create_store("nonexistent", _make_config())

    def test_custom_backend_registration(self) -> None:
        registry = GraphStoreRegistry.with_defaults()

        def _custom(config: Any) -> Any:
            return "custom_store"

        registry.register("custom", _custom)
        assert "custom" in registry
        store = registry.create_store("custom", _make_config())
        assert store == "custom_store"

    def test_backends_returns_registered_names(self) -> None:
        registry = GraphStoreRegistry.with_defaults()
        assert registry.backends() == [BACKEND_NEO4J, BACKEND_MEMORY]
