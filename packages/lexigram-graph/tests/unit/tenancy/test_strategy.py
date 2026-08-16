"""Tests for the GraphTenancyStrategy enum."""

from __future__ import annotations

from enum import Enum


class TestGraphTenancyStrategy:
    """Tests for the per-tenant graph isolation strategy enum."""

    def test_has_node_property(self) -> None:
        from lexigram.contracts.data.graph.tenancy import GraphTenancyStrategy
        assert GraphTenancyStrategy.NODE_PROPERTY.value == "node_property"

    def test_has_graph_per_tenant(self) -> None:
        from lexigram.contracts.data.graph.tenancy import GraphTenancyStrategy
        assert GraphTenancyStrategy.GRAPH_PER_TENANT.value == "graph_per_tenant"

    def test_is_str_enum(self) -> None:
        from lexigram.contracts.data.graph.tenancy import GraphTenancyStrategy
        assert issubclass(GraphTenancyStrategy, str)
        assert issubclass(GraphTenancyStrategy, Enum)
