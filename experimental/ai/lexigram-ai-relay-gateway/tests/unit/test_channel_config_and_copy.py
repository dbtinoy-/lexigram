"""Config-validation and copy-semantics tests for the relay gateway channels."""

from __future__ import annotations

import pytest

from channel_registry_support import (
    MODEL,
    SOURCE,
    build_registry,
    make_channel,
)
from lexigram.ai.relay.gateway.channels import RelayChannelRegistry
from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.contracts.ai.relay import RelayChannel


class TestCopySemantics:
    """Selection returns the configured channel without mutating config."""

    def test_selected_channel_is_frozen_and_equals_config_channel(self) -> None:
        channels = (make_channel("a"), make_channel("b"))
        config = RelayGatewayConfig(channels=channels)
        registry = RelayChannelRegistry(config)
        result = registry.select(SOURCE, MODEL)
        assert result.is_ok()
        selected = result.unwrap()
        assert isinstance(selected, RelayChannel)
        assert selected == channels[0]
        assert config.channels == channels

    def test_config_channels_never_reordered(self) -> None:
        channels = (
            make_channel("z", priority=1),
            make_channel("y", priority=2),
            make_channel("x", priority=3),
        )
        config = RelayGatewayConfig(channels=channels)
        registry = RelayChannelRegistry(config)
        first = registry.select(SOURCE, MODEL)
        second = registry.select(SOURCE, MODEL, preferred="x")
        assert first.is_ok()
        assert second.is_ok()
        assert first.unwrap().name == "z"
        assert second.unwrap().name == "x"
        assert config.channels == channels


class TestConfigValidation:
    """RelayGatewayConfig rejects duplicate channel names and bad auto-test config."""

    def test_duplicate_channel_names_raise(self) -> None:
        with pytest.raises(ValueError):
            RelayGatewayConfig(channels=(make_channel("dup"), make_channel("dup")))

    def test_empty_config_is_valid(self) -> None:
        config = RelayGatewayConfig()
        assert config.channels == ()
        assert config.model_suffix == {}
        assert config.provider_options == {}
        assert config.auto_test_channels is False
        assert config.auto_test_interval_seconds == 600

    def test_auto_test_fields_roundtrip(self) -> None:
        config = RelayGatewayConfig(
            channels=(make_channel("a"),),
            auto_test_channels=True,
            auto_test_interval_seconds=30,
        )
        assert config.auto_test_channels is True
        assert config.auto_test_interval_seconds == 30

    def test_zero_auto_test_interval_raises(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            RelayGatewayConfig(auto_test_interval_seconds=0)

    def test_negative_auto_test_interval_raises(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            RelayGatewayConfig(channels=(make_channel("a"),), auto_test_interval_seconds=-1)

    def test_max_upstream_retries_defaults_to_zero(self) -> None:
        config = RelayGatewayConfig()
        assert config.max_upstream_retries == 0

    def test_max_upstream_retries_roundtrip(self) -> None:
        config = RelayGatewayConfig(
            channels=(make_channel("a"),),
            max_upstream_retries=2,
        )
        assert config.max_upstream_retries == 2

    def test_negative_max_upstream_retries_raises(self) -> None:
        with pytest.raises(ValueError, match="retries"):
            RelayGatewayConfig(max_upstream_retries=-1)


class TestProviderOptionsAndSuffix:
    """model_suffix / provider_options round-trip and never affect selection."""

    def test_fields_roundtrip_and_selection_ignores_them(self) -> None:
        channels = (make_channel("a"),)
        config = RelayGatewayConfig(
            channels=channels,
            model_suffix={"a": ":thinking"},
            provider_options={"a": {"max_tokens": 8192}},
        )
        assert config.model_suffix == {"a": ":thinking"}
        assert config.provider_options == {"a": {"max_tokens": 8192}}
        registry = RelayChannelRegistry(config)
        result = registry.select(SOURCE, MODEL)
        assert result.is_ok()
        assert result.unwrap() == channels[0]
