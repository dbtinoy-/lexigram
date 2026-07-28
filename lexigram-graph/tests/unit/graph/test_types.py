"""Tests for graph types."""

from __future__ import annotations

import pytest

from lexigram.graph import types


class TestNodeId:
    """Tests for NodeId type alias."""

    def test_node_id_str(self) -> None:
        """Verify string node ID works."""
        node_id: types.NodeId = "node-123"
        assert node_id == "node-123"
        assert isinstance(node_id, str)

    def test_node_id_int(self) -> None:
        """Verify integer node ID works."""
        node_id: types.NodeId = 42
        assert node_id == 42
        assert isinstance(node_id, int)


class TestEdgeId:
    """Tests for EdgeId type alias."""

    def test_edge_id_str(self) -> None:
        """Verify string edge ID works."""
        edge_id: types.EdgeId = "edge-456"
        assert edge_id == "edge-456"
        assert isinstance(edge_id, str)

    def test_edge_id_int(self) -> None:
        """Verify integer edge ID works."""
        edge_id: types.EdgeId = 99
        assert edge_id == 99
        assert isinstance(edge_id, int)


class TestProperties:
    """Tests for Properties type alias."""

    def test_properties_dict(self) -> None:
        """Verify properties dict works."""
        props: types.Properties = {"name": "test", "value": 42}
        assert props["name"] == "test"
        assert props["value"] == 42

    def test_properties_empty(self) -> None:
        """Verify empty properties works."""
        props: types.Properties = {}
        assert len(props) == 0