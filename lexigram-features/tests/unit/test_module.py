"""Tests for FeatureFlagsModule."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from lexigram.features.config import FeatureFlagsConfig
from lexigram.features.module import FeatureFlagsModule


class TestFeatureFlagsModule:
    """Tests for FeatureFlagsModule."""

    def test_configure_returns_dynamic_module(self) -> None:
        """configure() returns a DynamicModule with providers."""
        module = FeatureFlagsModule.configure()
        assert module is not None
        assert module.module is FeatureFlagsModule
        assert len(module.providers) == 1

    def test_configure_with_config(self) -> None:
        """configure() accepts a FeatureFlagsConfig."""
        config = FeatureFlagsConfig(initial_flags={"beta": True})
        module = FeatureFlagsModule.configure(config=config)
        provider = module.providers[0]
        assert provider._config is config

    def test_configure_with_none_config(self) -> None:
        """configure() accepts None config."""
        module = FeatureFlagsModule.configure(config=None)
        assert module is not None

    def test_configure_raises_on_invalid_config(self) -> None:
        """configure() raises TypeError for non-FeatureFlagsConfig."""
        with pytest.raises(TypeError, match="config must be FeatureFlagsConfig"):
            FeatureFlagsModule.configure(config="invalid")

    def test_configure_exports_protocol(self) -> None:
        """configure() exports FlagProviderProtocol."""
        from lexigram.contracts.feature_flags import FlagProviderProtocol

        module = FeatureFlagsModule.configure()
        assert FlagProviderProtocol in module.exports

    def test_stub_returns_dynamic_module(self) -> None:
        """stub() returns a DynamicModule."""
        module = FeatureFlagsModule.stub()
        assert module is not None
        assert module.module is FeatureFlagsModule
        assert len(module.providers) == 1

    def test_stub_exports_protocol(self) -> None:
        """stub() exports FlagProviderProtocol."""
        from lexigram.contracts.feature_flags import FlagProviderProtocol

        module = FeatureFlagsModule.stub()
        assert FlagProviderProtocol in module.exports
