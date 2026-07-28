"""Unit tests for graph types."""

from __future__ import annotations

import pytest


class TestGraphTypeAliases:
    """Test type aliases for graph entities."""

    def test_node_id_is_str_or_int(self) -> None:
        """Verify NodeId accepts str or int."""
        from lexigram.graph.types import NodeId

        node_str: NodeId = "node-123"
        node_int: NodeId = 456
        assert isinstance(node_str, (str, int))
        assert isinstance(node_int, (str, int))

    def test_edge_id_is_str_or_int(self) -> None:
        """Verify EdgeId accepts str or int."""
        from lexigram.graph.types import EdgeId

        edge_str: EdgeId = "edge-789"
        edge_int: EdgeId = 101112
        assert isinstance(edge_str, (str, int))
        assert isinstance(edge_int, (str, int))

    def test_properties_is_dict(self) -> None:
        """Verify Properties is a dict alias."""
        from lexigram.graph.types import Properties

        props: Properties = {"name": "Alice", "age": 30}
        assert isinstance(props, dict)


class TestGraphTypeExports:
    """Test that types are properly exported."""

    def test_types_exported(self) -> None:
        """Verify all types are in __all__."""
        from lexigram.graph import types

        assert "NodeId" in types.__all__
        assert "EdgeId" in types.__all__
        assert "Properties" in types.__all__