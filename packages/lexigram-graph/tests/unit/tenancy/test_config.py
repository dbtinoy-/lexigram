"""Tests for the GraphTenancyConfig model."""

from __future__ import annotations


class TestGraphTenancyConfig:
    """Tests for the per-tenant graph tenancy config."""

    def test_defaults_disabled(self) -> None:
        from lexigram.graph.config import GraphTenancyConfig
        cfg = GraphTenancyConfig()
        assert cfg.enabled is False
        assert cfg.strategy == "node_property"
        assert cfg.template == "{logical}_t_{tenant}"

    def test_enabled_with_strategy(self) -> None:
        from lexigram.graph.config import GraphTenancyConfig
        cfg = GraphTenancyConfig(enabled=True, strategy="graph_per_tenant")
        assert cfg.enabled is True
        assert cfg.strategy == "graph_per_tenant"

    def test_custom_template(self) -> None:
        from lexigram.graph.config import GraphTenancyConfig
        cfg = GraphTenancyConfig(template="t_{tenant}_{logical}")
        assert cfg.template == "t_{tenant}_{logical}"

    def test_on_graph_config_defaults(self) -> None:
        from lexigram.graph.config import GraphConfig
        cfg = GraphConfig()
        assert cfg.tenancy.enabled is False
        assert cfg.tenancy.strategy == "node_property"

    def test_on_graph_config_with_tenancy(self) -> None:
        from lexigram.graph.config import GraphConfig, GraphTenancyConfig
        cfg = GraphConfig(tenancy=GraphTenancyConfig(enabled=True, strategy="graph_per_tenant"))
        assert cfg.tenancy.enabled is True
        assert cfg.tenancy.strategy == "graph_per_tenant"
