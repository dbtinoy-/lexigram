"""Config-alignment tests for SessionProvider."""

from __future__ import annotations

import pytest

from lexigram.ai.session.config import SessionConfig
from lexigram.ai.session.di.provider import SessionProvider


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
        provider = SessionProvider()
        assert provider.config_key == SessionConfig.config_section
        assert provider.config_model is SessionConfig

    @pytest.mark.asyncio
    async def test_injected_config_used_when_no_explicit(self) -> None:
        provider = SessionProvider()
        provider.config = SessionConfig(enabled=False)
        container = _FakeRegistrar()

        await provider.register(container)

        assert container.singletons[SessionConfig] is provider.config

    @pytest.mark.asyncio
    async def test_explicit_config_wins_over_injected(self) -> None:
        explicit = SessionConfig(enabled=True)
        provider = SessionProvider(config=explicit)
        provider.config = SessionConfig(enabled=False)
        container = _FakeRegistrar()

        await provider.register(container)

        assert container.singletons[SessionConfig] is explicit

    @pytest.mark.asyncio
    async def test_default_config_binds_when_nothing_supplied(self) -> None:
        provider = SessionProvider()
        container = _FakeRegistrar()

        await provider.register(container)

        assert isinstance(container.singletons[SessionConfig], SessionConfig)