"""Integration tests for lexigram-ui package."""

from __future__ import annotations

import pytest

from lexigram.ui.config import UIConfig
from lexigram.ui.di.provider import UIProvider


class TestUIProviderIntegration:
    """Integration tests for UIProvider basic functionality."""

    @pytest.mark.integration
    def test_provider_initialization_default(self):
        """Test UIProvider initialization with default config."""
        provider = UIProvider()
        assert provider.name == "ui"

    @pytest.mark.integration
    def test_provider_initialization_with_config(self):
        """Test UIProvider initialization with custom config."""
        config = UIConfig()
        provider = UIProvider(config=config)
        assert provider.name == "ui"

    @pytest.mark.integration
    def test_provider_has_required_attributes(self):
        """Test provider has required attributes."""
        provider = UIProvider()
        assert hasattr(provider, "name")

    @pytest.mark.integration
    def test_provider_priority(self):
        """Test provider has correct priority."""
        from lexigram.contracts.core.provider import ProviderPriority
        provider = UIProvider()
        assert provider.priority == ProviderPriority.PRESENTATION


class TestUIConfigIntegration:
    """Integration tests for UIConfig."""

    @pytest.mark.integration
    def test_ui_config_creation(self):
        """Test UIConfig can be created."""
        config = UIConfig()
        assert config is not None

    @pytest.mark.integration
    def test_ui_config_model_dump(self):
        """Test UIConfig model can be serialized."""
        config = UIConfig()
        config_dict = config.model_dump()
        assert isinstance(config_dict, dict)


class TestUIModuleIntegration:
    """Integration tests for UIModule."""

    @pytest.mark.integration
    def test_ui_module_import(self):
        """Test UIModule can be imported."""
        from lexigram.ui.module import UIModule
        assert UIModule is not None

    @pytest.mark.integration
    def test_ui_molecules_import(self):
        """Test UI molecules can be imported."""
        from lexigram.ui.molecules import Modal, Alert, InlineToast
        assert Modal is not None
        assert Alert is not None
        assert InlineToast is not None