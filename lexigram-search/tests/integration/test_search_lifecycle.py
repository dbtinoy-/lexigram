"""Integration tests for lexigram-search package."""

from __future__ import annotations

import pytest

from lexigram.search.config import SearchConfig
from lexigram.search.di.provider import SearchProvider


class TestSearchProviderIntegration:
    """Integration tests for SearchProvider basic functionality."""

    @pytest.mark.integration
    def test_provider_initialization_default(self):
        """Test SearchProvider initialization with default config."""
        from lexigram.search.backends.null import NullBackend
        backend = NullBackend()
        provider = SearchProvider(backend=backend)
        assert provider.name == "search"

    @pytest.mark.integration
    def test_provider_initialization_with_config(self):
        """Test SearchProvider initialization with custom config."""
        from lexigram.search.backends.null import NullBackend
        backend = NullBackend()
        config = SearchConfig()
        provider = SearchProvider(backend=backend, config=config)
        assert provider.name == "search"

    @pytest.mark.integration
    def test_provider_has_required_attributes(self):
        """Test provider has required attributes."""
        from lexigram.search.backends.null import NullBackend
        backend = NullBackend()
        provider = SearchProvider(backend=backend)
        assert hasattr(provider, "name")
        assert hasattr(provider, "backend")

    @pytest.mark.integration
    def test_provider_priority(self):
        """Test provider has correct priority."""
        from lexigram.contracts.core.provider import ProviderPriority
        from lexigram.search.backends.null import NullBackend
        backend = NullBackend()
        provider = SearchProvider(backend=backend)
        assert provider.priority == ProviderPriority.DOMAIN


class TestSearchConfigIntegration:
    """Integration tests for SearchConfig."""

    @pytest.mark.integration
    def test_search_config_creation(self):
        """Test SearchConfig can be created."""
        config = SearchConfig()
        assert config is not None

    @pytest.mark.integration
    def test_search_config_model_dump(self):
        """Test SearchConfig model can be serialized."""
        config = SearchConfig()
        config_dict = config.model_dump()
        assert isinstance(config_dict, dict)


class TestSearchModuleIntegration:
    """Integration tests for SearchModule."""

    @pytest.mark.integration
    def test_search_module_import(self):
        """Test SearchModule can be imported."""
        from lexigram.search.module import SearchModule
        assert SearchModule is not None

    @pytest.mark.integration
    def test_search_engine_import(self):
        """Test SearchEngine can be imported."""
        from lexigram.search.engine import SearchEngine
        assert SearchEngine is not None


class TestSearchBackendsIntegration:
    """Integration tests for search backends."""

    @pytest.mark.integration
    def test_null_backend_import(self):
        """Test NullBackend can be imported."""
        from lexigram.search.backends.null import NullBackend
        assert NullBackend is not None