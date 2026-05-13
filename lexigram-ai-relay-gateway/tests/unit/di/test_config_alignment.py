"""Config-alignment tests for RelayGatewayProvider."""

from __future__ import annotations

from lexigram.ai.relay.gateway.di.provider import RelayGatewayProvider


class TestConfigAlignment:
    def test_provider_is_explicit_only(self) -> None:
        provider = RelayGatewayProvider()
        assert provider.config_key is None
        assert provider.config_model is None