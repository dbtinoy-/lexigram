"""Tests for EvaluationProvider DI registration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, call

import pytest

from lexigram.ai.evaluation.config import EvaluationConfig
from lexigram.ai.evaluation.di.provider import EvaluationProvider
from lexigram.contracts.ai.evaluation import EvaluatorProtocol
from lexigram.contracts.core.health import HealthStatus


class TestEvaluationProvider:
    """Tests for EvaluationProvider."""

    def test_provider_name(self) -> None:
        assert EvaluationProvider.name == "evaluation"

    def test_default_config_created_when_none_given(self) -> None:
        provider = EvaluationProvider()
        assert isinstance(provider._config, EvaluationConfig)

    def test_custom_config_stored(self) -> None:
        config = EvaluationConfig(default_threshold=0.6)
        provider = EvaluationProvider(config=config)
        assert provider._config.default_threshold == 0.6

    @pytest.mark.asyncio
    async def test_register_registers_evaluators(self) -> None:
        provider = EvaluationProvider()
        container = MagicMock()
        container.singleton = MagicMock()
        await provider.register(container)
        names = {
            kw["name"]
            for _, kw in (
                (args, kwargs)
                for args, kwargs in (
                    (c.args, c.kwargs)
                    for c in container.singleton.call_args_list
                    if c.kwargs.get("name")
                )
            )
        }
        assert "criteria" in names
        assert "qa" in names
        assert "string_distance" in names
        assert "embedding_distance" in names

    @pytest.mark.asyncio
    async def test_register_registers_config_singleton(self) -> None:
        config = EvaluationConfig(default_threshold=0.55)
        provider = EvaluationProvider(config=config)
        container = MagicMock()
        container.singleton = MagicMock()
        await provider.register(container)
        calls_with_config = [
            c for c in container.singleton.call_args_list
            if c.args and c.args[0] is EvaluationConfig
        ]
        assert len(calls_with_config) == 1

    @pytest.mark.asyncio
    async def test_health_check_returns_healthy(self) -> None:
        provider = EvaluationProvider()
        result = await provider.health_check()
        assert result.status == HealthStatus.HEALTHY
        assert result.component == "evaluation"

    @pytest.mark.asyncio
    async def test_boot_does_not_raise(self) -> None:
        provider = EvaluationProvider()
        container = AsyncMock()
        await provider.boot(container)

    @pytest.mark.asyncio
    async def test_shutdown_does_not_raise(self) -> None:
        provider = EvaluationProvider()
        await provider.shutdown()
