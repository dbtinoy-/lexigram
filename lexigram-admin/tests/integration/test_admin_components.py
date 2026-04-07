"""Integration tests for lexigram-admin package lifecycle."""

from __future__ import annotations

import pytest

from lexigram.admin.config import AdminConfig
from lexigram.admin.di.bundle_provider import AdminProvider


class TestAdminProviderIntegration:
    """Integration tests for AdminProvider basic functionality."""

    @pytest.mark.integration
    def test_provider_initialization_default(self):
        """Test AdminProvider initialization with default config."""
        provider = AdminProvider()
        assert provider.name == "admin"

    @pytest.mark.integration
    def test_provider_initialization_with_config(self):
        """Test AdminProvider initialization with custom config."""
        config = AdminConfig()
        provider = AdminProvider(config=config)
        assert provider.name == "admin"

    @pytest.mark.integration
    def test_provider_has_required_attributes(self):
        """Test provider has required attributes."""
        provider = AdminProvider()
        assert hasattr(provider, "name")

    @pytest.mark.integration
    def test_provider_priority(self):
        """Test provider has correct priority."""
        from lexigram.contracts.core.provider import ProviderPriority
        provider = AdminProvider()
        assert provider.priority == ProviderPriority.APPLICATION


class TestAdminConfigIntegration:
    """Integration tests for AdminConfig."""

    @pytest.mark.integration
    def test_config_creation(self):
        """Test AdminConfig can be created."""
        config = AdminConfig()
        assert config is not None

    @pytest.mark.integration
    def test_config_model_dump(self):
        """Test AdminConfig model can be serialized."""
        config = AdminConfig()
        config_dict = config.model_dump()
        assert isinstance(config_dict, dict)

    @pytest.mark.integration
    def test_config_has_enabled(self):
        """Test AdminConfig has enabled field."""
        config = AdminConfig(enabled=True)
        assert config.enabled is True


class TestAdminModuleIntegration:
    """Integration tests for AdminModule."""

    @pytest.mark.integration
    def test_admin_module_import(self):
        """Test AdminModule can be imported."""
        from lexigram.admin.module import AdminModule
        assert AdminModule is not None