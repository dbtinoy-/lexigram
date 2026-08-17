"""Config-alignment tests for UIProvider."""

from __future__ import annotations

import pytest

from lexigram.ui.config import UIConfig
from lexigram.ui.di.provider import UIProvider


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
        provider = UIProvider()
        assert provider.config_key == UIConfig.config_section
        assert provider.config_model is UIConfig

    @pytest.mark.asyncio
    async def test_injected_config_used_when_no_explicit(self) -> None:
        provider = UIProvider()
        provider.config = UIConfig(title="Injected App")
        container = _FakeRegistrar()

        await provider.register(container)

        assert container.singletons[UIConfig] is provider.config

    @pytest.mark.asyncio
    async def test_explicit_config_wins_over_injected(self) -> None:
        explicit = UIConfig(title="Explicit App")
        provider = UIProvider(config=explicit)
        provider.config = UIConfig(title="Injected App")
        container = _FakeRegistrar()

        await provider.register(container)

        assert container.singletons[UIConfig] is explicit

    @pytest.mark.asyncio
    async def test_default_config_binds_when_nothing_supplied(self) -> None:
        provider = UIProvider()
        container = _FakeRegistrar()

        await provider.register(container)

        assert isinstance(container.singletons[UIConfig], UIConfig)