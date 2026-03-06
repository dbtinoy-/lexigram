"""Config binding tests for the SkillsProvider."""

from __future__ import annotations

import pytest

from lexigram.ai.skills.config import SkillsConfig
from lexigram.ai.skills.di.provider import SkillsProvider


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
async def test_skills_config_bound_when_requested() -> None:
    requested = SkillsConfig(cache_ttl_seconds=120)
    provider = SkillsProvider(config=requested)
    registrar = _FakeRegistrar()
    await provider.register(registrar)
    assert registrar.bindings[SkillsConfig] is requested


@pytest.mark.asyncio
async def test_skills_config_bound_with_defaults() -> None:
    provider = SkillsProvider()
    registrar = _FakeRegistrar()
    await provider.register(registrar)
    assert isinstance(registrar.bindings[SkillsConfig], SkillsConfig)