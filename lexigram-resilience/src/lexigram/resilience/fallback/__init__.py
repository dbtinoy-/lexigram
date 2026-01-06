"""Fallback pattern implementation for Lexigram Framework.

The Fallback pattern provides error recovery strategies for pipeline execution,
allowing operations to gracefully degrade or retry when failures occur.
"""

from __future__ import annotations

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

__all__ = [
    "AlternativeFallback",
    "DegradationConfig",
    "DegradationFallback",
    "Fallback",
    "FallbackStep",
    "FallbackStrategy",
    "RetryFallback",
    "alternative",
    "degrade",
    "retry_fallback",
]
