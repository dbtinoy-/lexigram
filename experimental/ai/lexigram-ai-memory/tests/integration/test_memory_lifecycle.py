"""Integration tests for lexigram-ai-memory package."""

from __future__ import annotations

import pytest

from lexigram.ai.memory.config import MemoryConfig
from lexigram.ai.memory.di.provider import MemoryProvider


class TestMemoryProviderIntegration:
    """Integration tests for MemoryProvider basic functionality."""

    @pytest.mark.integration
    def test_provider_initialization_default(self):
        """Test MemoryProvider initialization with default config."""
        provider = MemoryProvider()
        assert provider.name == "ai-memory"

    @pytest.mark.integration
    def test_provider_initialization_with_config(self):
        """Test MemoryProvider initialization with custom config."""
        config = MemoryConfig()
        provider = MemoryProvider(config=config)
        assert provider.name == "ai-memory"

    @pytest.mark.integration
    def test_provider_has_required_attributes(self):
        """Test provider has required attributes."""
        provider = MemoryProvider()
        assert hasattr(provider, "name")

    @pytest.mark.integration
    def test_provider_priority(self):
        """Test provider has correct priority."""
        from lexigram.contracts.core.provider import ProviderPriority
        provider = MemoryProvider()
        assert provider.priority == ProviderPriority.DOMAIN


class TestMemoryConfigIntegration:
    """Integration tests for MemoryConfig."""

    @pytest.mark.integration
    def test_memory_config_creation(self):
        """Test MemoryConfig can be created."""
        config = MemoryConfig()
        assert config is not None

    @pytest.mark.integration
    def test_memory_config_model_dump(self):
        """Test MemoryConfig model can be serialized."""
        config = MemoryConfig()
        config_dict = config.model_dump()
        assert isinstance(config_dict, dict)

    @pytest.mark.integration
    def test_memory_config_has_episodic(self):
        """Test MemoryConfig has episodic memory config."""
        config = MemoryConfig()
        assert hasattr(config, "episodic")

    @pytest.mark.integration
    def test_memory_config_has_semantic(self):
        """Test MemoryConfig has semantic memory config."""
        config = MemoryConfig()
        assert hasattr(config, "semantic")


class TestMemoryModuleIntegration:
    """Integration tests for MemoryModule."""

    @pytest.mark.integration
    def test_memory_module_import(self):
        """Test MemoryModule can be imported."""
        from lexigram.ai.memory.module import MemoryModule
        assert MemoryModule is not None


class TestMemoryStoresIntegration:
    """Integration tests for memory stores."""

    @pytest.mark.integration
    def test_episodic_store_import(self):
        """Test EpisodicMemoryStore can be imported."""
        from lexigram.ai.memory.episodic.store import EpisodicMemoryStore
        assert EpisodicMemoryStore is not None

    @pytest.mark.integration
    def test_semantic_store_import(self):
        """Test SemanticMemoryStore can be imported."""
        from lexigram.ai.memory.semantic.store import SemanticMemoryStore
        assert SemanticMemoryStore is not None

    @pytest.mark.integration
    def test_working_memory_import(self):
        """Test WorkingMemoryManager can be imported."""
        from lexigram.ai.memory.working.manager import WorkingMemoryManager
        assert WorkingMemoryManager is not None


class TestMemoryRetrievalIntegration:
    """Integration tests for memory retrieval."""

    @pytest.mark.integration
    def test_memory_retriever_import(self):
        """Test MemoryRetriever can be imported."""
        from lexigram.ai.memory.retrieval.retriever import MemoryRetriever
        assert MemoryRetriever is not None

    @pytest.mark.integration
    def test_relevance_ranker_import(self):
        """Test RelevanceRanker can be imported."""
        from lexigram.ai.memory.retrieval.ranking import RelevanceRanker
        assert RelevanceRanker is not None


class TestMemoryConsolidationIntegration:
    """Integration tests for memory consolidation."""

    @pytest.mark.integration
    def test_memory_consolidator_import(self):
        """Test MemoryConsolidator can be imported."""
        from lexigram.ai.memory.consolidation.consolidator import MemoryConsolidator
        assert MemoryConsolidator is not None

    @pytest.mark.integration
    def test_consolidation_scheduler_import(self):
        """Test ConsolidationScheduler can be imported."""
        from lexigram.ai.memory.consolidation.scheduler import ConsolidationScheduler
        assert ConsolidationScheduler is not None