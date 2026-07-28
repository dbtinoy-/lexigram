"""Integration tests for lexigram-graphql package lifecycle."""

from __future__ import annotations

import pytest

from lexigram.graphql.config import GraphQLConfig
from lexigram.graphql.di.provider import GraphQLProvider


class TestGraphQLProviderIntegration:
    """Integration tests for GraphQLProvider basic functionality."""

    @pytest.mark.integration
    def test_provider_initialization_default(self):
        """Test GraphQLProvider initialization with default config."""
        provider = GraphQLProvider()
        assert provider.name == "graphql"

    @pytest.mark.integration
    def test_provider_initialization_with_config(self):
        """Test GraphQLProvider initialization with custom config."""
        config = GraphQLConfig()
        provider = GraphQLProvider(config=config)
        assert provider.name == "graphql"

    @pytest.mark.integration
    def test_provider_has_required_attributes(self):
        """Test provider has required attributes."""
        provider = GraphQLProvider()
        assert hasattr(provider, "name")

    @pytest.mark.integration
    def test_provider_priority(self):
        """Test provider has correct priority."""
        from lexigram.contracts.core.provider import ProviderPriority
        provider = GraphQLProvider()
        assert provider.priority == ProviderPriority.PRESENTATION


class TestGraphQLConfigIntegration:
    """Integration tests for GraphQLConfig."""

    @pytest.mark.integration
    def test_config_creation(self):
        """Test GraphQLConfig can be created."""
        config = GraphQLConfig()
        assert config is not None

    @pytest.mark.integration
    def test_config_model_dump(self):
        """Test GraphQLConfig model can be serialized."""
        config = GraphQLConfig()
        config_dict = config.model_dump()
        assert isinstance(config_dict, dict)

    @pytest.mark.integration
    def test_config_has_enabled(self):
        """Test GraphQLConfig has enabled field."""
        config = GraphQLConfig(enabled=True)
        assert config.enabled is True


class TestGraphQLModuleIntegration:
    """Integration tests for GraphQLModule."""

    @pytest.mark.integration
    def test_graphql_module_import(self):
        """Test GraphQLModule can be imported."""
        from lexigram.graphql.module import GraphQLModule
        assert GraphQLModule is not None


class TestGraphQLSchemaIntegration:
    """Integration tests for GraphQL schema."""

    @pytest.mark.integration
    def test_schema_import(self):
        """Test GraphQL Schema can be imported."""
        from lexigram.graphql.schema import Schema
        assert Schema is not None