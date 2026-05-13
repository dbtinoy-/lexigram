"""Config-alignment tests for GuardProvider."""

from __future__ import annotations

import pytest

from lexigram.ai.guard.config import GuardConfig
from lexigram.ai.guard.di.provider import GuardProvider


class _FakeRegistrar:
    def __init__(self) -> None:
        self.singletons: dict[type, object] = {}

    def singleton(self, cls: type, instance: object) -> None:
        self.singletons[cls] = instance


class TestConfigAlignment:
    def test_provider_declares_config_key_and_model(self) -> None:
        provider = GuardProvider()
        assert provider.config_key == GuardConfig.config_section
        assert provider.config_model is GuardConfig

    @pytest.mark.asyncio
    async def test_injected_config_used_when_no_explicit(self) -> None:
        provider = GuardProvider()
        provider.config = GuardConfig(enabled=False)
        container = _FakeRegistrar()

        await provider.register(container)

        assert container.singletons[GuardConfig] is provider.config

    @pytest.mark.asyncio
    async def test_explicit_config_wins_over_injected(self) -> None:
        explicit = GuardConfig(enabled=True)
        provider = GuardProvider(config=explicit)
        provider.config = GuardConfig(enabled=False)
        container = _FakeRegistrar()

        await provider.register(container)

        assert container.singletons[GuardConfig] is explicit

    @pytest.mark.asyncio
    async def test_default_config_binds_when_nothing_supplied(self) -> None:
        provider = GuardProvider()
        container = _FakeRegistrar()

        await provider.register(container)

        assert isinstance(container.singletons[GuardConfig], GuardConfig)