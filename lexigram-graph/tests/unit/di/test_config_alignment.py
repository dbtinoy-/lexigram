"""Config-alignment tests for GraphProvider."""

from __future__ import annotations

import pytest

from lexigram.graph.config import GraphConfig
from lexigram.graph.di.provider import GraphProvider


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
        provider = GraphProvider()
        assert provider.config_key == GraphConfig.config_section
        assert provider.config_model is GraphConfig

    @pytest.mark.asyncio
    async def test_injected_config_used_when_no_explicit(self) -> None:
        provider = GraphProvider()
        provider.config = GraphConfig(enabled=False)
        container = _FakeRegistrar()

        await provider.register(container)

        assert container.singletons[GraphConfig] is provider.config

    @pytest.mark.asyncio
    async def test_explicit_config_wins_over_injected(self) -> None:
        explicit = GraphConfig(enabled=True)
        provider = GraphProvider(config=explicit)
        provider.config = GraphConfig(enabled=False)
        container = _FakeRegistrar()

        await provider.register(container)

        assert container.singletons[GraphConfig] is explicit

    @pytest.mark.asyncio
    async def test_default_config_binds_when_nothing_supplied(self) -> None:
        provider = GraphProvider()
        container = _FakeRegistrar()

        await provider.register(container)

        assert isinstance(container.singletons[GraphConfig], GraphConfig)