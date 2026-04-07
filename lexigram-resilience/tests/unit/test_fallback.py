"""Unit tests for fallback module."""

from __future__ import annotations

import asyncio

import pytest

from lexigram.contracts.infra.resilience.models import RetryConfig
from lexigram.resilience.fallback.fallback import (
    Fallback,
    alternative,
    degrade,
    retry_fallback,
)
from lexigram.resilience.fallback.models import DegradationConfig, FallbackStrategy
from lexigram.resilience.fallback.steps import (
    AlternativeFallback,
    DegradationFallback,
    FallbackStep,
    RetryFallback,
)
from lexigram.result import Err, Ok


class TestFallbackStrategy:
    """Tests for FallbackStrategy enum."""

    def test_retry_value(self) -> None:
        assert FallbackStrategy.RETRY == "retry"

    def test_circuit_breaker_value(self) -> None:
        assert FallbackStrategy.CIRCUIT_BREAKER == "circuit_breaker"

    def test_degradation_value(self) -> None:
        assert FallbackStrategy.DEGRADATION == "degradation"

    def test_alternative_value(self) -> None:
        assert FallbackStrategy.ALTERNATIVE == "alternative"


class TestDegradationConfig:
    """Tests for DegradationConfig."""

    def test_default_values(self) -> None:
        config = DegradationConfig()
        assert config.degraded_result is None
        assert config.log_level is None

    def test_custom_degraded_result(self) -> None:
        config = DegradationConfig(degraded_result="fallback_value")
        assert config.degraded_result == "fallback_value"

    def test_custom_log_level(self) -> None:
        config = DegradationConfig(log_level=10)
        assert config.log_level == 10


class TestFallbackClass:
    """Tests for Fallback high-level API."""

    def test_retry_fallback_creates_retry_fallback(self) -> None:
        config = RetryConfig(max_attempts=3)
        result = Fallback.retry_fallback(config)
        assert isinstance(result, RetryFallback)
        assert result.config == config

    def test_degrade_creates_degradation_fallback(self) -> None:
        result = Fallback.degrade("fallback")
        assert isinstance(result, DegradationFallback)
        assert result.config.degraded_result == "fallback"

    def test_degrade_with_none(self) -> None:
        result = Fallback.degrade()
        assert isinstance(result, DegradationFallback)
        assert result.config.degraded_result is None

    def test_alternative_creates_alternative_fallback(self) -> None:
        async def alt_fn(ctx, err):
            return Ok("alternative")

        result = Fallback.alternative(alt_fn)
        assert isinstance(result, AlternativeFallback)


class TestFallbackModuleFunctions:
    """Tests for module-level fallback functions."""

    def test_degrade_function(self) -> None:
        result = degrade("test_value")
        assert isinstance(result, DegradationFallback)
        assert result.config.degraded_result == "test_value"

    def test_retry_fallback_function(self) -> None:
        config = RetryConfig(max_attempts=5)
        result = retry_fallback(config)
        assert isinstance(result, RetryFallback)
        assert result.config == config

    def test_alternative_function(self) -> None:
        async def alt_fn(ctx, err):
            return Ok("alt")

        result = alternative(alt_fn)
        assert isinstance(result, AlternativeFallback)


class TestRetryFallback:
    """Tests for RetryFallback."""

    @pytest.fixture
    def retry_config(self) -> RetryConfig:
        return RetryConfig(max_attempts=3, base_delay=0.01)

    def test_initialization(self, retry_config: RetryConfig) -> None:
        fallback = RetryFallback(retry_config)
        assert fallback.config == retry_config
        assert "retry_" in fallback.name

    @pytest.mark.asyncio
    async def test_execute_with_retries(self, retry_config: RetryConfig) -> None:
        fallback = RetryFallback(retry_config)
        context: dict[str, object] = {}

        class FakeError(Exception):
            pass

        result = await fallback.execute(context, FakeError("test error"))
        assert result.is_ok()
        assert result.unwrap() == "__RETRY__"
        # Context key includes the fallback's unique name
        context_keys = [k for k in context.keys() if k.startswith("_attempts_")]
        assert len(context_keys) == 1

    @pytest.mark.asyncio
    async def test_execute_retry_exhausted(self) -> None:
        # Create a config with max_attempts=1
        retry_config = RetryConfig(max_attempts=1, base_delay=0.001)
        fallback = RetryFallback(retry_config)
        # Set context with attempts already at max
        fallback_name = fallback.name
        context: dict[str, object] = {f"_attempts_{fallback_name}": 1}

        class FakeError(Exception):
            pass

        result = await fallback.execute(context, FakeError("test error"))
        assert result.is_err()
        assert "Retry exhausted" in str(result.unwrap_err())


class TestDegradationFallback:
    """Tests for DegradationFallback."""

    @pytest.fixture
    def degradation_config(self) -> DegradationConfig:
        return DegradationConfig(degraded_result="fallback_value")

    def test_initialization(self, degradation_config: DegradationConfig) -> None:
        fallback = DegradationFallback(degradation_config)
        assert fallback.config == degradation_config
        assert "degradation_" in fallback.name

    @pytest.mark.asyncio
    async def test_execute_returns_degraded_result(
        self,
        degradation_config: DegradationConfig,
    ) -> None:
        fallback = DegradationFallback(degradation_config)
        result = await fallback.execute({}, ValueError("test error"))

        assert result.is_ok()
        assert result.unwrap() == "fallback_value"

    @pytest.mark.asyncio
    async def test_execute_with_none_result(self) -> None:
        config = DegradationConfig(degraded_result=None)
        fallback = DegradationFallback(config)
        result = await fallback.execute({}, ValueError("test error"))

        assert result.is_ok()
        assert result.unwrap() is None


class TestAlternativeFallback:
    """Tests for AlternativeFallback."""

    @pytest.mark.asyncio
    async def test_execute_calls_function(self) -> None:
        async def alt_fn(ctx, err):
            return Ok(f"handled {type(err).__name__}")

        fallback = AlternativeFallback(alt_fn)
        result = await fallback.execute({}, ValueError("test"))

        assert result.is_ok()
        assert result.unwrap() == "handled ValueError"

    @pytest.mark.asyncio
    async def test_execute_returns_err_from_function(self) -> None:
        async def alt_fn(ctx, err):
            return Err(ValueError("alternative failed"))

        fallback = AlternativeFallback(alt_fn)
        result = await fallback.execute({}, ValueError("original"))

        assert result.is_err()


class TestFallbackStep:
    """Tests for FallbackStep abstract base class."""

    def test_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            FallbackStep("test")
