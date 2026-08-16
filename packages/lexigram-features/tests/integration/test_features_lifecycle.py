"""Integration tests for lexigram-features package."""

from __future__ import annotations

import pytest

from lexigram.features.config import FeatureFlagsConfig
from lexigram.features.di.provider import FeatureFlagsProvider


class TestFeatureFlagsProviderIntegration:
    """Integration tests for FeatureFlagsProvider basic functionality."""

    @pytest.mark.integration
    def test_provider_initialization_default(self):
        """Test FeatureFlagsProvider initialization with default config."""
        provider = FeatureFlagsProvider()
        assert provider.name == "features"

    @pytest.mark.integration
    def test_provider_initialization_with_config(self):
        """Test FeatureFlagsProvider initialization with custom config."""
        config = FeatureFlagsConfig()
        provider = FeatureFlagsProvider(config=config)
        assert provider.name == "features"

    @pytest.mark.integration
    def test_provider_from_config(self):
        """Test FeatureFlagsProvider from_config factory."""
        config = FeatureFlagsConfig()
        provider = FeatureFlagsProvider.from_config(config)
        assert provider.name == "features"

    @pytest.mark.integration
    def test_provider_has_required_attributes(self):
        """Test provider has required attributes."""
        provider = FeatureFlagsProvider()
        assert hasattr(provider, "name")


class TestFeatureFlagsConfigIntegration:
    """Integration tests for FeatureFlagsConfig."""

    @pytest.mark.integration
    def test_feature_flags_config_creation(self):
        """Test FeatureFlagsConfig can be created."""
        config = FeatureFlagsConfig()
        assert config is not None

    @pytest.mark.integration
    def test_feature_flags_config_model_dump(self):
        """Test FeatureFlagsConfig model can be serialized."""
        config = FeatureFlagsConfig()
        config_dict = config.model_dump()
        assert isinstance(config_dict, dict)


class TestFlagManagerIntegration:
    """Integration tests for FlagManager."""

    @pytest.mark.integration
    def test_flag_manager_import(self):
        """Test FlagManager can be imported."""
        from lexigram.features.manager import FlagManager
        assert FlagManager is not None

    @pytest.mark.integration
    def test_local_provider_import(self):
        """Test LocalProvider can be imported."""
        from lexigram.features.backends.local import LocalProvider
        assert LocalProvider is not None