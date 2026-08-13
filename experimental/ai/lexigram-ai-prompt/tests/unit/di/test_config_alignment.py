"""Config-alignment tests for PromptProvider."""

from __future__ import annotations

import pytest

from lexigram.ai.prompt.config import PromptConfig
from lexigram.ai.prompt.di.provider import PromptProvider


class _FakeRegistrar:
    def __init__(self) -> None:
        self.singletons: dict[type, object] = {}

    def singleton(self, cls: type, instance: object) -> None:
        self.singletons[cls] = instance


class TestConfigAlignment:
    def test_provider_declares_config_key_and_model(self) -> None:
        provider = PromptProvider()
        assert provider.config_key == PromptConfig.config_section
        assert provider.config_model is PromptConfig

    @pytest.mark.asyncio
    async def test_injected_config_used_when_no_explicit(self) -> None:
        provider = PromptProvider()
        provider.config = PromptConfig(enabled=False)
        container = _FakeRegistrar()

        await provider.register(container)

        assert container.singletons[PromptConfig] is provider.config

    @pytest.mark.asyncio
    async def test_explicit_config_wins_over_injected(self) -> None:
        explicit = PromptConfig(enabled=True)
        provider = PromptProvider(config=explicit)
        provider.config = PromptConfig(enabled=False)
        container = _FakeRegistrar()

        await provider.register(container)

        assert container.singletons[PromptConfig] is explicit

    @pytest.mark.asyncio
    async def test_default_config_binds_when_nothing_supplied(self) -> None:
        provider = PromptProvider()
        container = _FakeRegistrar()

        await provider.register(container)

        assert isinstance(container.singletons[PromptConfig], PromptConfig)