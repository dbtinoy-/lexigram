"""Unit tests for AI guard module."""

import pytest
from unittest.mock import MagicMock

from lexigram.ai.guard import GuardModule
from lexigram.ai.guard.config import GuardConfig


class TestGuardModule:
    """Test GuardModule functionality."""

    def test_module_creation(self):
        """Test module can be created."""
        module = GuardModule()
        assert module is not None

    def test_module_with_config(self):
        """Test module creation with config."""
        config = GuardConfig(
            injection_detection=True,
            pii_detection=True,
        )
        mod = GuardModule.configure(config=config)
        assert mod is not None
        assert mod.module is GuardModule
        assert len(mod.providers) == 1

    def test_module_providers(self):
        """Test module returns provider list."""
        mod = GuardModule.configure()
        providers = mod.providers
        assert len(providers) == 1


class TestGuardModuleConfiguration:
    """Test guard module configuration."""

    def test_config_defaults(self):
        """Test default configuration values."""
        config = GuardConfig()
        assert config.injection_detection is True
        assert config.pii_detection is True
        assert config.enabled is True

    def test_config_with_custom_values(self):
        """Test configuration with custom values."""
        config = GuardConfig(
            injection_detection=False,
            pii_detection=False,
            pii_action="block",
        )
        assert config.injection_detection is False
        assert config.pii_detection is False
        assert config.pii_action == "block"

