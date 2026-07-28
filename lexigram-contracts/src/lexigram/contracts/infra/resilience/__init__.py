"""Resilience pattern protocols."""

from __future__ import annotations

from lexigram.contracts.infra.resilience.enums import CircuitState
from lexigram.contracts.infra.resilience.exceptions import (
    BulkheadError,
    CircuitBreakerError,
    CircuitOpenError,
    FallbackError,
    ResilienceError,
    RetryError,
    RetryExhaustedError,
)
from lexigram.contracts.infra.resilience.models import (
    CircuitBreakerConfig,
    RetryConfig,
    TimeoutConfig,
)
from lexigram.contracts.infra.resilience.protocols import (
    BulkheadProtocol,
    CircuitBreakerProtocol,
    CircuitBreakerRegistryProtocol,
    RateLimiterProtocol,
    ResilienceFallbackProtocol,
    ResiliencePipelineFactoryProtocol,
    ResiliencePipelineProtocol,
    RetryPolicyProtocol,
    ThrottlerProtocol,
    TimeoutProtocol,
)

__all__ = [
    "BulkheadError",
    "BulkheadProtocol",
    "CircuitBreakerConfig",
    "CircuitBreakerError",
    "CircuitBreakerProtocol",
    "CircuitBreakerRegistryProtocol",
    "CircuitOpenError",
    "CircuitState",
    "FallbackError",
    "RateLimiterProtocol",
    "ResilienceError",
    "ResilienceFallbackProtocol",
    "ResiliencePipelineFactoryProtocol",
    "ResiliencePipelineProtocol",
    "RetryConfig",
    "RetryError",
    "RetryExhaustedError",
    "RetryPolicyProtocol",
    "ThrottlerProtocol",
    "TimeoutConfig",
    "TimeoutProtocol",
]
