"""Config-alignment tests for MemoryProvider."""

from __future__ import annotations

import pytest

from lexigram.ai.memory.config import MemoryConfig
from lexigram.ai.memory.di.provider import MemoryProvider


class _FakeRegistrar:
    def __init__(self) -> None:
        self.singletons: dict[type, object] = {}

    def singleton(self, cls: type, instance: object) -> None:
        self.singletons[cls] = instance


class TestConfigAlignment:
    def test_provider_declares_config_key_and_model(self) -> None:
        provider = MemoryProvider()
        assert provider.config_key == MemoryConfig.config_section
        assert provider.config_model is MemoryConfig

    @pytest.mark.asyncio
    async def test_injected_config_used_when_no_explicit(self) -> None:
        provider = MemoryProvider()
        provider.config = MemoryConfig(enabled=False)
        container = _FakeRegistrar()

        await provider.register(container)

        assert container.singletons[MemoryConfig] is provider.config

    @pytest.mark.asyncio
    async def test_explicit_config_wins_over_injected(self) -> None:
        explicit = MemoryConfig(enabled=True)
        provider = MemoryProvider(config=explicit)
        provider.config = MemoryConfig(enabled=False)
        container = _FakeRegistrar()

        await provider.register(container)

        assert container.singletons[MemoryConfig] is explicit

    @pytest.mark.asyncio
    async def test_default_config_binds_when_nothing_supplied(self) -> None:
        provider = MemoryProvider()
        container = _FakeRegistrar()

        await provider.register(container)

        assert isinstance(container.singletons[MemoryConfig], MemoryConfig)