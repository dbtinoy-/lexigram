"""Circuit breaker preset policies.

Encapsulates the tuned configuration profiles exposed as
:class:`~lexigram.resilience.circuit.breaker.CircuitBreaker` classmethods.
"""

from __future__ import annotations

from lexigram.contracts.infra.resilience.models import CircuitBreakerConfig


def sensitive_config() -> CircuitBreakerConfig:
    """Build the fast-trip preset — for critical dependencies.

    Opens after 3 consecutive failures or a 30 % failure rate.  Waits only
    30 s before probing recovery, and requires just 1 probe success to close
    again.  Use for primary databases, auth services, or any dependency
    whose failure should be surfaced to callers as soon as possible.
    """
    return CircuitBreakerConfig(
        failure_threshold=3,
        recovery_timeout=30.0,
        success_threshold=1,
        failure_rate_threshold=0.3,
    )


def tolerant_config() -> CircuitBreakerConfig:
    """Build the slow-trip preset — for non-critical or high-volume dependencies.

    Opens only after 10 consecutive failures or a 70 % failure rate.  Waits
    120 s before probing recovery, and requires 5 consecutive probe successes
    before closing.  Use for analytics sinks, notification services, or any
    call whose failures should not immediately surface to callers.
    """
    return CircuitBreakerConfig(
        failure_threshold=10,
        recovery_timeout=120.0,
        success_threshold=5,
        failure_rate_threshold=0.7,
    )
