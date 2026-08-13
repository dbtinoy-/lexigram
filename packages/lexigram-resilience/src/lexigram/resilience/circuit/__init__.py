"""Circuit breaker resilience pattern."""

from __future__ import annotations

from lexigram.resilience.circuit.backend import (
    CircuitBreakerBackend,
    CircuitBreakerState,
    DistributedCircuitBreakerBackend,
    InMemoryCircuitBreakerBackend,
)
from lexigram.resilience.circuit.breaker import (
    CircuitBreaker,
    CircuitBreakerMetrics,
    CircuitBreakerRegistry,
    CircuitState,
    circuit_breaker,
    circuit_breaker_sync,
)
from lexigram.resilience.circuit.timeout import (
    ResilienceTimeoutError,
    timeout_context,
)

__all__ = [
    "CircuitBreaker",
    "CircuitBreakerBackend",
    "CircuitBreakerMetrics",
    "CircuitBreakerRegistry",
    "CircuitBreakerState",
    "CircuitState",
    "DistributedCircuitBreakerBackend",
    "InMemoryCircuitBreakerBackend",
    "ResilienceTimeoutError",
    "circuit_breaker",
    "circuit_breaker_sync",
    "timeout_context",
]
