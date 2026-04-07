"""Integration tests for lexigram-ai package."""

from __future__ import annotations
from enum import Enum

import pytest

from lexigram.ai.config import AIConfig
from lexigram.ai.di.provider import AIProvider


class TestAIProviderIntegration:
    """Integration tests for AIProvider basic functionality."""

    @pytest.mark.integration
    def test_provider_initialization_default(self):
        """Test AIProvider initialization with default config."""
        provider = AIProvider()
        assert provider.name == "ai"

    @pytest.mark.integration
    def test_provider_initialization_with_config(self):
        """Test AIProvider initialization with custom config."""
        config = AIConfig()
        provider = AIProvider(config=config)
        assert provider.name == "ai"

    @pytest.mark.integration
    def test_provider_has_required_attributes(self):
        """Test provider has required attributes."""
        provider = AIProvider()
        assert hasattr(provider, "name")

    @pytest.mark.integration
    def test_provider_has_priority(self):
        """Test provider has priority attribute."""
        provider = AIProvider()
        assert hasattr(provider, "priority")

    @pytest.mark.integration
    def test_provider_priority_value(self):
        """Test provider has correct priority value."""
        from lexigram.contracts.core.provider import ProviderPriority
        provider = AIProvider()
        assert provider.priority == ProviderPriority.DOMAIN


class TestAIConfigIntegration:
    """Integration tests for AIConfig."""

    @pytest.mark.integration
    def test_ai_config_creation(self):
        """Test AIConfig can be created."""
        config = AIConfig()
        assert config is not None

    @pytest.mark.integration
    def test_ai_config_model_dump(self):
        """Test AIConfig model can be serialized."""
        config = AIConfig()
        config_dict = config.model_dump()
        assert isinstance(config_dict, dict)

    @pytest.mark.integration
    def test_ai_config_has_llm_config(self):
        """Test AIConfig has LLM configuration."""
        config = AIConfig()
        assert hasattr(config, "llm")

    @pytest.mark.integration
    def test_ai_config_has_rag_config(self):
        """Test AIConfig has RAG configuration."""
        config = AIConfig()
        assert hasattr(config, "rag")

    @pytest.mark.integration
    def test_ai_config_has_vector_config(self):
        """Test AIConfig has vector configuration."""
        config = AIConfig()
        assert hasattr(config, "vector")

    @pytest.mark.integration
    def test_ai_config_has_governance_config(self):
        """Test AIConfig has governance configuration."""
        config = AIConfig()
        assert hasattr(config, "governance")


class TestAIModuleIntegration:
    """Integration tests for AIModule."""

    @pytest.mark.integration
    def test_ai_module_import(self):
        """Test AIModule can be imported."""
        from lexigram.ai.module import AIModule
        assert AIModule is not None

    @pytest.mark.integration
    def test_ai_module_has_configure_method(self):
        """Test AIModule has configure method."""
        from lexigram.ai.module import AIModule
        assert hasattr(AIModule, "configure")


class TestAIProviderProtocolIntegration:
    """Integration tests for AIProviderProtocol."""

    @pytest.mark.integration
    def test_ai_provider_protocol_import(self):
        """Test AIProviderProtocol can be imported."""
        from lexigram.contracts.ai import AIProviderProtocol
        assert AIProviderProtocol is not None


class TestGovernanceConfigIntegration:
    """Integration tests for GovernanceConfig."""

    @pytest.mark.integration
    def test_governance_config_import(self):
        """Test GovernanceConfig can be imported."""
        from lexigram.ai.config import GovernanceConfig
        assert GovernanceConfig is not None