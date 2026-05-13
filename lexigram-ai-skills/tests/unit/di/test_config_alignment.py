"""Config-alignment tests for SkillsProvider."""

from __future__ import annotations

import pytest

from lexigram.ai.skills.config import SkillsConfig
from lexigram.ai.skills.di.provider import SkillsProvider


class _FakeRegistrar:
    def __init__(self) -> None:
        self.singletons: dict[type, object] = {}

    def singleton(self, cls: type, instance: object = None) -> None:
        self.singletons[cls] = instance


class TestConfigAlignment:
    def test_provider_declares_config_key_and_model(self) -> None:
        provider = SkillsProvider()
        assert provider.config_key == SkillsConfig.config_section
        assert provider.config_model is SkillsConfig

    @pytest.mark.asyncio
    async def test_injected_config_used_when_no_explicit(self) -> None:
        provider = SkillsProvider()
        provider.config = SkillsConfig(enabled=False)
        container = _FakeRegistrar()

        await provider.register(container)

        assert container.singletons[SkillsConfig] is provider.config

    @pytest.mark.asyncio
    async def test_explicit_config_wins_over_injected(self) -> None:
        explicit = SkillsConfig(enabled=True)
        provider = SkillsProvider(config=explicit)
        provider.config = SkillsConfig(enabled=False)
        container = _FakeRegistrar()

        await provider.register(container)

        assert container.singletons[SkillsConfig] is explicit

    @pytest.mark.asyncio
    async def test_default_config_binds_when_nothing_supplied(self) -> None:
        provider = SkillsProvider()
        container = _FakeRegistrar()

        await provider.register(container)

        assert isinstance(container.singletons[SkillsConfig], SkillsConfig)