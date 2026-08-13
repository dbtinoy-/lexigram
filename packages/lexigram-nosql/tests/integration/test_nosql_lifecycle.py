"""Integration tests for lexigram-nosql package."""

from __future__ import annotations

import pytest

from lexigram.nosql.config import NoSQLConfig
from lexigram.nosql.di.provider import NoSQLProvider


class TestNoSQLProviderIntegration:
    """Integration tests for NoSQLProvider basic functionality."""

    @pytest.mark.integration
    def test_provider_initialization_default(self):
        """Test NoSQLProvider initialization with default config."""
        provider = NoSQLProvider()
        assert provider.name == "nosql"

    @pytest.mark.integration
    def test_provider_initialization_with_config(self):
        """Test NoSQLProvider initialization with custom config."""
        config = NoSQLConfig()
        provider = NoSQLProvider(config=config)
        assert provider.name == "nosql"

    @pytest.mark.integration
    def test_provider_from_config(self):
        """Test NoSQLProvider from_config factory."""
        config = NoSQLConfig()
        provider = NoSQLProvider.from_config(config)
        assert provider.name == "nosql"

    @pytest.mark.integration
    def test_provider_has_required_attributes(self):
        """Test provider has required attributes."""
        provider = NoSQLProvider()
        assert hasattr(provider, "name")

    @pytest.mark.integration
    def test_provider_priority(self):
        """Test provider has correct priority."""
        from lexigram.contracts.core.provider import ProviderPriority
        provider = NoSQLProvider()
        assert provider.priority == ProviderPriority.INFRASTRUCTURE


class TestNoSQLConfigIntegration:
    """Integration tests for NoSQLConfig."""

    @pytest.mark.integration
    def test_nosql_config_creation(self):
        """Test NoSQLConfig can be created."""
        config = NoSQLConfig()
        assert config is not None

    @pytest.mark.integration
    def test_nosql_config_model_dump(self):
        """Test NoSQLConfig model can be serialized."""
        config = NoSQLConfig()
        config_dict = config.model_dump()
        assert isinstance(config_dict, dict)


class TestNoSQLModuleIntegration:
    """Integration tests for NoSQLModule."""

    @pytest.mark.integration
    def test_nosql_module_import(self):
        """Test NoSQLModule can be imported."""
        from lexigram.nosql.module import NoSQLModule
        assert NoSQLModule is not None

    @pytest.mark.integration
    def test_nosql_protocols_import(self):
        """Test NoSQL protocols can be imported."""
        from lexigram.nosql.protocols import DocumentStoreProtocol
        assert DocumentStoreProtocol is not None