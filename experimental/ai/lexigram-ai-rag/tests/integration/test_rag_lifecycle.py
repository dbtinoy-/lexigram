"""Integration tests for lexigram-ai-rag package."""

from __future__ import annotations

import pytest

from lexigram.ai.rag.config import RAGConfig
from lexigram.ai.rag.di.provider import RAGProvider


class TestRAGProviderIntegration:
    """Integration tests for RAGProvider basic functionality."""

    @pytest.mark.integration
    def test_provider_initialization_default(self):
        """Test RAGProvider initialization with default config."""
        provider = RAGProvider()
        assert provider.name == "rag"

    @pytest.mark.integration
    def test_provider_initialization_with_config(self):
        """Test RAGProvider initialization with custom config."""
        config = RAGConfig()
        provider = RAGProvider(config=config)
        assert provider.name == "rag"

    @pytest.mark.integration
    def test_provider_has_required_attributes(self):
        """Test provider has required attributes."""
        provider = RAGProvider()
        assert hasattr(provider, "name")

    @pytest.mark.integration
    def test_provider_priority(self):
        """Test provider has correct priority."""
        from lexigram.contracts.core.provider import ProviderPriority
        provider = RAGProvider()
        assert provider.priority == ProviderPriority.DOMAIN


class TestRAGConfigIntegration:
    """Integration tests for RAGConfig."""

    @pytest.mark.integration
    def test_rag_config_creation(self):
        """Test RAGConfig can be created."""
        config = RAGConfig()
        assert config is not None

    @pytest.mark.integration
    def test_rag_config_model_dump(self):
        """Test RAGConfig model can be serialized."""
        config = RAGConfig()
        config_dict = config.model_dump()
        assert isinstance(config_dict, dict)


class TestRAGModuleIntegration:
    """Integration tests for RAGModule."""

    @pytest.mark.integration
    def test_rag_module_import(self):
        """Test RAGModule can be imported."""
        from lexigram.ai.rag.module import RAGModule
        assert RAGModule is not None


class TestRAGPipelineIntegration:
    """Integration tests for RAG pipeline components."""

    @pytest.mark.integration
    def test_rag_pipeline_import(self):
        """Test RAGPipeline can be imported."""
        from lexigram.ai.rag.pipeline import RAGPipeline
        assert RAGPipeline is not None