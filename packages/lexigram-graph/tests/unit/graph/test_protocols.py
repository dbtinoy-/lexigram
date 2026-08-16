"""Tests for graph protocols."""

from __future__ import annotations

from typing import Protocol

import pytest

from lexigram.contracts.data.graph.protocols import (
    GraphProtocol as ContractsGraphProtocol,
    GraphStoreProtocol as ContractsGraphStoreProtocol,
)
from lexigram.graph.protocols import GraphProtocol, GraphStoreProtocol


class TestGraphProtocol:
    """Tests for GraphProtocol."""

    def test_graph_protocol_is_protocol(self) -> None:
        """Verify GraphProtocol is a Protocol."""
        assert issubclass(GraphProtocol, Protocol)

    def test_graph_protocol_is_runtime_checkable(self) -> None:
        """Verify GraphProtocol is runtime checkable."""
        import inspect

        assert inspect.isclass(GraphProtocol)
        assert hasattr(GraphProtocol, "__instancecheck__")

    def test_graph_protocol_is_re_exported_from_contracts(self) -> None:
        """Verify GraphProtocol is the same as the contracts version."""
        assert GraphProtocol is ContractsGraphProtocol

    def test_graph_protocol_has_expected_methods(self) -> None:
        """Verify GraphProtocol defines expected methods."""
        assert hasattr(GraphProtocol, "create_node")
        assert hasattr(GraphProtocol, "get_node")
        assert hasattr(GraphProtocol, "find_nodes")
        assert hasattr(GraphProtocol, "create_edge")
        assert hasattr(GraphProtocol, "traverse")
        assert hasattr(GraphProtocol, "shortest_path")
        assert hasattr(GraphProtocol, "query")


class TestGraphStoreProtocol:
    """Tests for GraphStoreProtocol."""

    def test_graph_store_protocol_is_protocol(self) -> None:
        """Verify GraphStoreProtocol is a Protocol."""
        assert issubclass(GraphStoreProtocol, Protocol)

    def test_graph_store_protocol_is_runtime_checkable(self) -> None:
        """Verify GraphStoreProtocol is runtime checkable."""
        import inspect

        assert inspect.isclass(GraphStoreProtocol)
        assert hasattr(GraphStoreProtocol, "__instancecheck__")

    def test_graph_store_protocol_is_re_exported_from_contracts(self) -> None:
        """Verify GraphStoreProtocol is the same as the contracts version."""
        assert GraphStoreProtocol is ContractsGraphStoreProtocol

    def test_graph_store_protocol_has_expected_methods(self) -> None:
        """Verify GraphStoreProtocol defines expected methods."""
        assert hasattr(GraphStoreProtocol, "connect")
        assert hasattr(GraphStoreProtocol, "disconnect")
        assert hasattr(GraphStoreProtocol, "health_check")
        assert hasattr(GraphStoreProtocol, "get_graph")
        assert hasattr(GraphStoreProtocol, "list_graphs")
        assert hasattr(GraphStoreProtocol, "create_graph")
        assert hasattr(GraphStoreProtocol, "delete_graph")


class TestProtocolsModule:
    """Tests for the protocols module itself."""

    def test_protocols_all_exports(self) -> None:
        """Verify __all__ contains both protocols."""
        from lexigram.graph import protocols

        assert "GraphProtocol" in protocols.__all__
        assert "GraphStoreProtocol" in protocols.__all__

    def test_protocols_all_length(self) -> None:
        """Verify __all__ has exactly 2 entries."""
        from lexigram.graph import protocols

        assert len(protocols.__all__) == 2
