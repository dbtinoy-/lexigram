"""Config precedence tests for the EvaluationProvider."""

from __future__ import annotations

import pytest

from lexigram.ai.evaluation.config import EvaluationConfig
from lexigram.ai.evaluation.di.provider import EvaluationProvider


class _FakeRegistrar:
    """Minimal registrar recording singleton bindings."""

    def __init__(self) -> None:
        self.bindings: dict[object, object] = {}

    def singleton(
        self, key: object, instance: object | None = None, **kwargs: object
    ) -> None:
        resolved = instance if instance is not None else kwargs.get("instance", key)
        self.bindings[key] = resolved


@pytest.mark.asyncio
async def test_config_section_matches_provider_key() -> None:
    assert EvaluationProvider.config_key == "ai_evaluation"
    assert EvaluationConfig.config_section == "ai_evaluation"


@pytest.mark.asyncio
async def test_explicit_config_wins_over_injected() -> None:
    requested = EvaluationConfig(default_threshold=0.9)
    injected = EvaluationConfig(default_threshold=0.5)
    provider = EvaluationProvider(config=requested)
    provider.config = injected
    registrar = _FakeRegistrar()
    await provider.register(registrar)
    assert registrar.bindings[EvaluationConfig] is requested


@pytest.mark.asyncio
async def test_injected_config_used_when_no_explicit() -> None:
    injected = EvaluationConfig(default_threshold=0.5)
    provider = EvaluationProvider()
    provider.config = injected
    registrar = _FakeRegistrar()
    await provider.register(registrar)
    assert registrar.bindings[EvaluationConfig] is injected


@pytest.mark.asyncio
async def test_defaults_when_neither() -> None:
    provider = EvaluationProvider()
    registrar = _FakeRegistrar()
    await provider.register(registrar)
    bound = registrar.bindings[EvaluationConfig]
    assert isinstance(bound, EvaluationConfig)
    assert bound.enabled is True