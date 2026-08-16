from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from lexigram.contracts.infra.resilience.models import RetryConfig
from lexigram.resilience.fallback.models import DegradationConfig
from lexigram.resilience.fallback.steps import (
    AlternativeFallback,
    DegradationFallback,
    RetryFallback,
)
from lexigram.result import Result

T = TypeVar("T")


class Fallback:
    """High-level API for creating fallback steps."""

    @staticmethod
    def retry_fallback(config: RetryConfig) -> RetryFallback:
        """Create a retry-based fallback step."""
        return RetryFallback(config)

    @staticmethod
    def degrade(degraded_result: Any = None) -> DegradationFallback:
        """Create a degradation fallback."""
        return DegradationFallback(DegradationConfig(degraded_result=degraded_result))

    @staticmethod
    def alternative(
        func: Callable[[Any, Exception], Awaitable[Result[Any, Exception]]],
    ) -> AlternativeFallback:
        """Create an alternative operation fallback."""
        return AlternativeFallback(func)


def degrade(degraded_result: Any = None) -> DegradationFallback:
    """Create a degradation fallback."""
    return Fallback.degrade(degraded_result)


def alternative(
    func: Callable[[Any, Exception], Awaitable[Result[Any, Exception]]],
) -> AlternativeFallback:
    """Create an alternative operation fallback."""
    return Fallback.alternative(func)


def retry_fallback(config: RetryConfig) -> RetryFallback:
    """Create a retry-based fallback step.

    Args:
        config: Retry configuration settings.

    Returns:
        A RetryFallback step configured with the given settings.
    """
    return Fallback.retry_fallback(config)
