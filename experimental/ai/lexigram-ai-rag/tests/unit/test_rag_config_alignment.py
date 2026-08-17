"""Config-system alignment tests for the RAG package."""

from __future__ import annotations

import pytest

from lexigram.ai.rag.config import RAGConfig, RAGTenancyConfig
from lexigram.ai.rag.di.provider import RAGProvider


class _FakeRegistrar:
    """Minimal registrar recording singleton bindings."""

    def __init__(self) -> None:
        self.bindings: dict[object, object] = {}

    def singleton(
        self, key: object, instance: object | None = None, **kwargs: object
    ) -> None:
        resolved = instance if instance is not None else kwargs.get("instance", key)
        self.bindings[key] = resolved

    def register(self, *args: object, **kwargs: object) -> None:  # noqa: ARG002
        pass


@pytest.mark.asyncio
async def test_config_section_matches_provider_key() -> None:
    """The provider config_key must equal the YAML/env section key."""
    assert RAGProvider.config_key == "ai_rag"
    assert RAGConfig.config_section == "ai_rag"


@pytest.mark.asyncio
async def test_tenancy_config_is_single_definition() -> None:
    """RAGConfig.tenancy must be an instance of the module RAGTenancyConfig."""
    assert isinstance(RAGConfig().tenancy, RAGTenancyConfig)


@pytest.mark.asyncio
async def test_explicit_config_wins_over_injected() -> None:
    """Constructor config must not be overwritten by injected section config."""
    requested = RAGConfig(top_k=2)
    injected = RAGConfig(top_k=8)
    provider = RAGProvider(config=requested)
    provider.config = injected
    registrar = _FakeRegistrar()
    await provider.register(registrar)
    assert registrar.bindings[RAGConfig] is requested


@pytest.mark.asyncio
async def test_injected_config_used_when_no_explicit() -> None:
    """Injected section config is used when the caller passed none."""
    injected = RAGConfig(top_k=8)
    provider = RAGProvider()
    provider.config = injected
    registrar = _FakeRegistrar()
    await provider.register(registrar)
    assert registrar.bindings[RAGConfig] is injected


@pytest.mark.asyncio
async def test_defaults_when_neither() -> None:
    """Both absent falls back to fresh defaults."""
    provider = RAGProvider()
    registrar = _FakeRegistrar()
    await provider.register(registrar)
    bound = registrar.bindings[RAGConfig]
    assert isinstance(bound, RAGConfig)
    assert bound.top_k == 5