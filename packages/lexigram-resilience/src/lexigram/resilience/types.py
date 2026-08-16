"""Type definitions for the resilience subsystem."""

from __future__ import annotations

from enum import StrEnum, auto

from lexigram.contracts.infra.resilience.enums import CircuitState as CircuitState
from lexigram.contracts.infra.resilience.models import (
    CircuitBreakerConfig as CircuitBreakerConfig,
)
from lexigram.contracts.infra.resilience.models import RetryConfig as RetryConfig
from lexigram.contracts.infra.resilience.models import TimeoutConfig as TimeoutConfig


class ResilienceStatus(StrEnum):
    """Status enum for Resilience."""

    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"


__all__ = [
    "BulkheadConfig",
    "CircuitBreakerConfig",
    "CircuitState",
    "IdempotencyResult",
    "IdempotencyStatus",
    "ResilienceStatus",
    "RetryConfig",
    "TimeoutConfig",
]


# === Idempotency Types (merged from idempotency/types.py) ===

from dataclasses import dataclass


class IdempotencyStatus(StrEnum):
    """Status of an idempotency-keyed operation."""

    PENDING = auto()
    COMPLETE = auto()
    EXPIRED = auto()


@dataclass(frozen=True)
class IdempotencyResult:
    """Result of processing an idempotency-keyed request.

    Attributes:
        is_duplicate: True if this request was already processed.
        key: The idempotency key.
        from_cache: True if the response was served from cache.
    """

    is_duplicate: bool
    key: str
    from_cache: bool = False
