"""Config-alignment tests for GraphQLProvider."""

from __future__ import annotations

import pytest

from lexigram.graphql.config import GraphQLConfig
from lexigram.graphql.di.provider import GraphQLProvider


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
        provider = GraphQLProvider()
        assert provider.config_key == GraphQLConfig.config_section
        assert provider.config_model is GraphQLConfig

    @pytest.mark.asyncio
    async def test_injected_config_used_when_no_explicit(self) -> None:
        provider = GraphQLProvider()
        provider.config = GraphQLConfig(debug=False)
        container = _FakeRegistrar()

        await provider.boot(container)

        assert provider.config is provider.config

    @pytest.mark.asyncio
    async def test_explicit_config_wins_over_injected(self) -> None:
        explicit = GraphQLConfig(debug=True)
        provider = GraphQLProvider(config=explicit)
        provider.config = GraphQLConfig(debug=False)
        container = _FakeRegistrar()

        await provider.boot(container)

        assert provider.config is explicit