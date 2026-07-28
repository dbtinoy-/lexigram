"""Tests for VectorModule."""

from __future__ import annotations

from lexigram.di.module import DynamicModule
from lexigram.vector.module import VectorModule


class TestVectorModule:
    def test_vector_module_exists(self) -> None:
        assert VectorModule is not None

    def test_configure_returns_dynamic_module(self) -> None:
        result = VectorModule.configure()
        assert isinstance(result, DynamicModule)
        assert result.module is VectorModule

    def test_stub_returns_dynamic_module(self) -> None:
        result = VectorModule.stub()
        assert isinstance(result, DynamicModule)
        assert result.module is VectorModule
