"""Config-alignment tests for TenancyProvider."""

from __future__ import annotations

import pytest

from lexigram.tenancy.config import TenancyConfig
from lexigram.tenancy.di.provider import TenancyProvider


class _FakeRegistrar:
    def __init__(self) -> None:
        self.singletons: dict[type, object] = {}

    def singleton(
        self, cls: type, instance: object = None, factory: object = None
    ) -> None:
        self.singletons[cls] = factory if factory is not None else instance

    def transient(self, *args: object, **kwargs: object) -> None:
        pass

    def has(self, cls: type) -> bool:
        return False


class TestConfigAlignment:
    def test_provider_declares_config_key_and_model(self) -> None:
        provider = TenancyProvider()
        assert provider.config_key == TenancyConfig.config_section
        assert provider.config_model is TenancyConfig

    @pytest.mark.asyncio
    async def test_injected_config_used_when_no_explicit(self) -> None:
        provider = TenancyProvider()
        provider.config = TenancyConfig(default_tenant="injected")
        container = _FakeRegistrar()

        await provider.register(container)

        assert provider._config is provider.config

    @pytest.mark.asyncio
    async def test_explicit_config_wins_over_injected(self) -> None:
        explicit = TenancyConfig(default_tenant="explicit")
        provider = TenancyProvider(config=explicit)
        provider.config = TenancyConfig(default_tenant="injected")
        container = _FakeRegistrar()

        await provider.register(container)

        assert provider._config is explicit

    @pytest.mark.asyncio
    async def test_default_config_used_when_nothing_supplied(self) -> None:
        provider = TenancyProvider()
        container = _FakeRegistrar()

        await provider.register(container)

        assert isinstance(provider._config, TenancyConfig)