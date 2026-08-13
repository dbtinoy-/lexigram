"""Config-alignment tests for QueueProvider."""

from __future__ import annotations

import pytest

from lexigram.queue.config import QueueConfig
from lexigram.queue.di.provider import QueueProvider


class _FakeRegistrar:
    def __init__(self) -> None:
        self.singletons: dict[type, object] = {}

    def singleton(
        self,
        cls: type,
        instance: object = None,
        factory: object = None,
        name: str | None = None,
    ) -> None:
        self.singletons[cls] = factory if factory is not None else instance

    def transient(self, *args: object, **kwargs: object) -> None:
        pass


class TestConfigAlignment:
    def test_provider_declares_config_key_and_model(self) -> None:
        provider = QueueProvider()
        assert provider.config_key == QueueConfig.config_section
        assert provider.config_model is QueueConfig

    @pytest.mark.asyncio
    async def test_injected_config_used_when_no_explicit(self) -> None:
        provider = QueueProvider()
        provider.config = QueueConfig(max_retries=3)
        container = _FakeRegistrar()

        await provider.register(container)

        assert container.singletons[QueueConfig] is provider.config

    @pytest.mark.asyncio
    async def test_explicit_config_wins_over_injected(self) -> None:
        explicit = QueueConfig(max_retries=9)
        provider = QueueProvider(config=explicit)
        provider.config = QueueConfig(max_retries=3)
        container = _FakeRegistrar()

        await provider.register(container)

        assert container.singletons[QueueConfig] is explicit

    @pytest.mark.asyncio
    async def test_default_config_binds_when_nothing_supplied(self) -> None:
        provider = QueueProvider()
        container = _FakeRegistrar()

        await provider.register(container)

        assert isinstance(container.singletons[QueueConfig], QueueConfig)