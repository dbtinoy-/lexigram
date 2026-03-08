"""Config-alignment tests for WorkersProvider."""

from __future__ import annotations

import pytest

from lexigram.ai.workers.config import WorkersConfig
from lexigram.ai.workers.di.provider import WorkersProvider


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
        provider = WorkersProvider()
        assert provider.config_key == WorkersConfig.config_section
        assert provider.config_model is WorkersConfig

    @pytest.mark.asyncio
    async def test_injected_config_used_when_no_explicit(self) -> None:
        provider = WorkersProvider()
        provider.config = WorkersConfig(enabled=False)
        container = _FakeRegistrar()

        await provider.register(container)

        assert container.singletons[WorkersConfig] is provider.config

    @pytest.mark.asyncio
    async def test_explicit_config_wins_over_injected(self) -> None:
        explicit = WorkersConfig(enabled=True)
        provider = WorkersProvider(config=explicit)
        provider.config = WorkersConfig(enabled=False)
        container = _FakeRegistrar()

        await provider.register(container)

        assert container.singletons[WorkersConfig] is explicit

    @pytest.mark.asyncio
    async def test_default_config_binds_when_nothing_supplied(self) -> None:
        provider = WorkersProvider()
        container = _FakeRegistrar()

        await provider.register(container)

        assert isinstance(container.singletons[WorkersConfig], WorkersConfig)