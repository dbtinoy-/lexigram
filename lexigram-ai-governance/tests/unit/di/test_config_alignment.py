"""Config-alignment tests for GovernanceProvider."""

from __future__ import annotations

import pytest

from lexigram.ai.governance.config import GovernanceConfig
from lexigram.ai.governance.di.provider import GovernanceProvider


class _FakeRegistrar:
    def __init__(self) -> None:
        self.singletons: dict[type, object] = {}

    def singleton(self, cls: type, instance: object) -> None:
        self.singletons[cls] = instance


class TestConfigAlignment:
    def test_provider_declares_config_key_and_model(self) -> None:
        provider = GovernanceProvider()
        assert provider.config_key == GovernanceConfig.config_section
        assert provider.config_model is GovernanceConfig

    @pytest.mark.asyncio
    async def test_injected_config_used_when_no_explicit(self) -> None:
        provider = GovernanceProvider()
        provider.config = GovernanceConfig(enabled=False)
        container = _FakeRegistrar()

        await provider.register(container)

        assert container.singletons[GovernanceConfig] is provider.config

    @pytest.mark.asyncio
    async def test_explicit_config_wins_over_injected(self) -> None:
        explicit = GovernanceConfig(enabled=True)
        provider = GovernanceProvider(config=explicit)
        provider.config = GovernanceConfig(enabled=False)
        container = _FakeRegistrar()

        await provider.register(container)

        assert container.singletons[GovernanceConfig] is explicit

    @pytest.mark.asyncio
    async def test_default_config_binds_when_nothing_supplied(self) -> None:
        provider = GovernanceProvider()
        container = _FakeRegistrar()

        await provider.register(container)

        assert isinstance(container.singletons[GovernanceConfig], GovernanceConfig)