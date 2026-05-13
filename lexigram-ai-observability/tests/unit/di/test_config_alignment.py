"""Config-alignment tests for ObservabilityProvider."""

from __future__ import annotations

import pytest

from lexigram.ai.observability.config import ObservabilityConfig
from lexigram.ai.observability.di.provider import ObservabilityProvider


class _FakeRegistrar:
    def __init__(self) -> None:
        self.singletons: dict[type, object] = {}

    def singleton(
        self, cls: type, instance: object = None, factory: object = None
    ) -> None:
        self.singletons[cls] = factory if factory is not None else instance

    def transient(self, *args: object, **kwargs: object) -> None:
        pass


class TestConfigAlignment:
    def test_provider_declares_config_key_and_model(self) -> None:
        provider = ObservabilityProvider()
        assert provider.config_key == ObservabilityConfig.config_section
        assert provider.config_model is ObservabilityConfig

    @pytest.mark.asyncio
    async def test_injected_config_used_when_no_explicit(self) -> None:
        provider = ObservabilityProvider()
        provider.config = ObservabilityConfig(enabled=False)
        container = _FakeRegistrar()

        await provider.register(container)

        assert container.singletons[ObservabilityConfig] is provider.config

    @pytest.mark.asyncio
    async def test_explicit_config_wins_over_injected(self) -> None:
        explicit = ObservabilityConfig(enabled=True)
        provider = ObservabilityProvider(config=explicit)
        provider.config = ObservabilityConfig(enabled=False)
        container = _FakeRegistrar()

        await provider.register(container)

        assert container.singletons[ObservabilityConfig] is explicit

    @pytest.mark.asyncio
    async def test_default_config_binds_when_nothing_supplied(self) -> None:
        provider = ObservabilityProvider()
        container = _FakeRegistrar()

        await provider.register(container)

        assert isinstance(container.singletons[ObservabilityConfig], ObservabilityConfig)