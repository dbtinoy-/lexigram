"""Config-alignment tests for VectorProvider."""

from __future__ import annotations

import pytest

from lexigram.vector.config import VectorConfig
from lexigram.vector.di.provider import VectorProvider


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
        provider = VectorProvider()
        assert provider.config_key == VectorConfig.config_section
        assert provider.config_model is VectorConfig

    @pytest.mark.asyncio
    async def test_injected_config_used_when_no_explicit(self) -> None:
        provider = VectorProvider()
        provider.config = VectorConfig(enabled=False)
        container = _FakeRegistrar()

        await provider.register(container)

        assert container.singletons[VectorConfig] is provider.config

    @pytest.mark.asyncio
    async def test_explicit_config_wins_over_injected(self) -> None:
        explicit = VectorConfig(enabled=True)
        provider = VectorProvider(config=explicit)
        provider.config = VectorConfig(enabled=False)
        container = _FakeRegistrar()

        await provider.register(container)

        assert container.singletons[VectorConfig] is explicit

    @pytest.mark.asyncio
    async def test_default_config_binds_when_nothing_supplied(self) -> None:
        provider = VectorProvider()
        container = _FakeRegistrar()

        await provider.register(container)

        assert isinstance(container.singletons[VectorConfig], VectorConfig)