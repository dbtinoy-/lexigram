"""Integration tests for lexigram-vector package."""

from __future__ import annotations

import pytest

from lexigram.vector.config import VectorConfig
from lexigram.vector.di.provider import VectorProvider


class TestVectorProviderIntegration:
    """Integration tests for VectorProvider basic functionality."""

    @pytest.mark.integration
    def test_provider_initialization_default(self):
        """Test VectorProvider initialization with default config."""
        provider = VectorProvider()
        assert provider.name == "vector"

    @pytest.mark.integration
    def test_provider_initialization_with_config(self):
        """Test VectorProvider initialization with custom config."""
        config = VectorConfig()
        provider = VectorProvider(config=config)
        assert provider.name == "vector"

    @pytest.mark.integration
    def test_provider_has_required_attributes(self):
        """Test provider has required attributes."""
        provider = VectorProvider()
        assert hasattr(provider, "name")

    @pytest.mark.integration
    def test_provider_priority(self):
        """Test provider has correct priority."""
        from lexigram.contracts.core.provider import ProviderPriority
        provider = VectorProvider()
        assert provider.priority == ProviderPriority.INFRASTRUCTURE


class TestVectorConfigIntegration:
    """Integration tests for VectorConfig."""

    @pytest.mark.integration
    def test_vector_config_creation(self):
        """Test VectorConfig can be created."""
        config = VectorConfig()
        assert config is not None

    @pytest.mark.integration
    def test_vector_config_model_dump(self):
        """Test VectorConfig model can be serialized."""
        config = VectorConfig()
        config_dict = config.model_dump()
        assert isinstance(config_dict, dict)


class TestVectorModuleIntegration:
    """Integration tests for VectorModule."""

    @pytest.mark.integration
    def test_vector_module_import(self):
        """Test VectorModule can be imported."""
        from lexigram.vector.module import VectorModule
        assert VectorModule is not None

    @pytest.mark.integration
    def test_vector_protocol_import(self):
        """Test VectorStoreProtocol can be imported."""
        from lexigram.contracts.data.vector.protocols import VectorStoreProtocol
        assert VectorStoreProtocol is not None