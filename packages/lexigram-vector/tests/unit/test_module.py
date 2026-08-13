from __future__ import annotations

from lexigram.contracts.data.vector.protocols import VectorStoreProtocol
from lexigram.di.module import DynamicModule, Module
from lexigram.vector.config import VectorConfig
from lexigram.vector.di.provider import VectorProvider
from lexigram.vector.module import VectorModule


def test_vector_module_has_configure() -> None:
    """VectorModule must have configure() classmethod."""
    assert hasattr(VectorModule, "configure")
    assert callable(VectorModule.configure)


def test_vector_module_configure_returns_dynamic_module() -> None:
    """VectorModule.configure() must return DynamicModule."""
    result = VectorModule.configure()
    assert isinstance(result, DynamicModule)


def test_vector_module_configure_exports_protocols() -> None:
    """VectorModule exports must include VectorStoreProtocol."""
    module = VectorModule.configure()

    assert len(module.exports) > 0
    assert VectorStoreProtocol in module.exports


def test_vector_module_uses_module_decorator() -> None:
    """VectorModule must use @module decorator semantics."""
    assert issubclass(VectorModule, Module)


def test_vector_module_configure_wires_provider_with_config() -> None:
    """configure() must register a configured VectorProvider."""
    config = VectorConfig(backend="memory")

    dynamic_module = VectorModule.configure(config=config)

    assert dynamic_module.module is VectorModule
    assert len(dynamic_module.providers) == 1
    provider = dynamic_module.providers[0]
    assert isinstance(provider, VectorProvider)
    assert provider._config is config
