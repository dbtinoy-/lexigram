from __future__ import annotations

from lexigram.contracts.data.graph.protocols import (
    GraphProtocol,
    GraphStoreProtocol,
)
from lexigram.di.module import DynamicModule, Module
from lexigram.graph.config import GraphConfig
from lexigram.graph.di.provider import GraphProvider
from lexigram.graph.module import GraphModule


def test_graph_module_has_configure() -> None:
    """GraphModule must have configure() classmethod."""
    assert hasattr(GraphModule, "configure")
    assert callable(GraphModule.configure)


def test_graph_module_configure_returns_dynamic_module() -> None:
    """GraphModule.configure() must return DynamicModule."""
    result = GraphModule.configure()
    assert isinstance(result, DynamicModule)


def test_graph_module_configure_exports_protocols() -> None:
    """GraphModule exports must include GraphStoreProtocol and GraphProtocol."""
    module = GraphModule.configure()

    # module.exports should be a list of protocol classes
    assert len(module.exports) > 0
    # Verify at least the core protocols are exported
    assert GraphStoreProtocol in module.exports
    assert GraphProtocol in module.exports


def test_graph_module_uses_module_decorator() -> None:
    """GraphModule must use @module decorator semantics."""
    assert issubclass(GraphModule, Module)


def test_graph_module_configure_wires_provider_with_config() -> None:
    """configure() must register a configured GraphProvider."""
    config = GraphConfig(backend="memory")

    dynamic_module = GraphModule.configure(config=config)

    assert dynamic_module.module is GraphModule
    assert len(dynamic_module.providers) == 1
    provider = dynamic_module.providers[0]
    assert isinstance(provider, GraphProvider)
    assert provider._effective_config is config
