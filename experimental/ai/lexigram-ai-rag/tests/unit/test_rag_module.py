"""Tests for RAG module."""

from __future__ import annotations

import pytest

from lexigram.ai.rag import RAGModule
from lexigram.contracts.ai.rag import RAGPipelineProtocol, RetrievalStrategyProtocol
from lexigram.di.module import DynamicModule


class TestRAGModule:
    """Test suite for RAGModule."""

    def test_module_decorator_exists(self) -> None:
        """Verify @module decorator is applied to RAGModule."""
        assert hasattr(RAGModule, '__lexigram_module__')

    def test_configure_returns_dynamic_module(self) -> None:
        """Verify configure() returns DynamicModule instance."""
        result = RAGModule.configure()
        assert isinstance(result, DynamicModule)
        assert result.module is RAGModule

    def test_configure_exports_rag_protocols(self) -> None:
        """Verify configure() exports RAG protocols."""
        result = RAGModule.configure()
        assert RAGPipelineProtocol in result.exports
        assert RetrievalStrategyProtocol in result.exports

    def test_configure_with_dict_config(self) -> None:
        """Verify configure() accepts dict configuration."""
        config = {"strategy": "bm25"}
        result = RAGModule.configure(config)
        assert isinstance(result, DynamicModule)
        assert result.module is RAGModule
