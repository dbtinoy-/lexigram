"""Lexigram Resilience — core resilience patterns packaged with lexigram.

Exposes circuit breakers, retries, bulkheads, timeouts, throttling, and
related tools used throughout the framework.

Usage::

    from lexigram.resilience import retry, circuit_breaker, BulkheadConfig

No auxiliary package is required; everything lives under
``lexigram.resilience``.  The contracts layer remains separate and only
contains the abstract protocols/configurations.
"""

from __future__ import annotations

import importlib.metadata

__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from typing import TYPE_CHECKING

from lexigram.resilience.constants import __version__ as __version__

if TYPE_CHECKING:
    from lexigram.contracts.exceptions import (
        BulkheadError,
        CircuitBreakerError,
        ResilienceError,
        RetryError,
    )
    from lexigram.contracts.infra.resilience import (
        BulkheadProtocol,
        CircuitBreakerProtocol,
        CircuitBreakerRegistryProtocol,
        ResiliencePipelineProtocol,
        RetryPolicyProtocol,
        ThrottlerProtocol,
    )
    from lexigram.contracts.infra.resilience.models import (
        CircuitBreakerConfig,
        RetryConfig,
        TimeoutConfig,
    )
    from lexigram.resilience.bulkhead import Bulkhead
    from lexigram.resilience.circuit import (
        CircuitBreaker,
        CircuitBreakerRegistry,
        CircuitState,
        DistributedCircuitBreakerBackend,
        InMemoryCircuitBreakerBackend,
        circuit_breaker,
    )
    from lexigram.resilience.config import BulkheadConfig as BulkheadConfig
    from lexigram.resilience.decorators import (
        bulkhead,
        circuit_breaker,
        circuit_breaker_sync,
        with_timeout,
    )
    from lexigram.resilience.exceptions import (
        BulkheadRejectedError,
        CircuitOpenError,
        ResilienceTimeoutError,
        RetryExhaustedError,
    )
    from lexigram.resilience.rate_limiter import (
        DistributedRateLimiter,
        RateLimiter,
        SlidingWindowLimiter,
    )
    from lexigram.resilience.retry import RetryPolicy
    from lexigram.resilience.retry.retry import retry
    from lexigram.resilience.throttle import Throttler
    from lexigram.resilience.timeout import TimeoutManager
    from lexigram.resilience.types import ResilienceStatus as ResilienceStatus

_LAZY_IMPORTS: dict[str, str] = {
    # contracts — protocols
    "BulkheadProtocol": "lexigram.contracts.infra.resilience",
    "CircuitBreakerProtocol": "lexigram.contracts.infra.resilience",
    "CircuitBreakerRegistryProtocol": "lexigram.contracts.infra.resilience",
    "ResiliencePipelineProtocol": "lexigram.contracts.infra.resilience",
    "RetryPolicyProtocol": "lexigram.contracts.infra.resilience",
    "ThrottlerProtocol": "lexigram.contracts.infra.resilience",
    # contracts — models/configs
    "BulkheadConfig": "lexigram.resilience.config",
    "CircuitBreakerConfig": "lexigram.contracts.infra.resilience.models",
    "ResilienceStatus": "lexigram.resilience.types",
    "RetryConfig": "lexigram.contracts.infra.resilience.models",
    "TimeoutConfig": "lexigram.contracts.infra.resilience.models",
    # exceptions — base classes remain in contracts
    "BulkheadError": "lexigram.contracts.exceptions",
    "CircuitBreakerError": "lexigram.contracts.exceptions",
    "ResilienceError": "lexigram.contracts.exceptions",
    "RetryError": "lexigram.contracts.exceptions",
    # exceptions — leaf exceptions
    "BulkheadRejectedError": "lexigram.resilience.exceptions",
    "CircuitOpenError": "lexigram.resilience.exceptions",
    "RetryExhaustedError": "lexigram.resilience.exceptions",
    "ResilienceTimeoutError": "lexigram.resilience.exceptions",
    # implementations
    "Bulkhead": "lexigram.resilience.bulkhead",
    "CircuitBreaker": "lexigram.resilience.circuit",
    "CircuitBreakerRegistry": "lexigram.resilience.circuit",
    "CircuitState": "lexigram.resilience.circuit",
    "DistributedCircuitBreakerBackend": "lexigram.resilience.circuit",
    "InMemoryCircuitBreakerBackend": "lexigram.resilience.circuit",
    "circuit_breaker": "lexigram.resilience.decorators",
    "circuit_breaker_sync": "lexigram.resilience.decorators",
    "bulkhead": "lexigram.resilience.decorators",
    "with_timeout": "lexigram.resilience.decorators",
    "RateLimiter": "lexigram.resilience.rate_limiter",
    "SlidingWindowLimiter": "lexigram.resilience.rate_limiter",
    "DistributedRateLimiter": "lexigram.resilience.rate_limiter",
    "RetryPolicy": "lexigram.resilience.retry",
    "ResiliencePipeline": "lexigram.resilience.pipeline.executor",
    "retry": "lexigram.resilience.retry.retry",
    "Throttler": "lexigram.resilience.throttle",
    # constants
    "DEFAULT_BULKHEAD_MAX_CONCURRENT": "lexigram.resilience.constants",
    "DEFAULT_CB_FAILURE_THRESHOLD": "lexigram.resilience.constants",
    "DEFAULT_CB_RECOVERY_TIMEOUT": "lexigram.resilience.constants",
    "DEFAULT_RATE_LIMIT_WINDOW": "lexigram.resilience.constants",
    "DEFAULT_RETRY_ATTEMPTS": "lexigram.resilience.constants",
    "DEFAULT_RETRY_DELAY": "lexigram.resilience.constants",
    "DEFAULT_TIMEOUT": "lexigram.resilience.constants",
    # --- added by migration script ---
    "ResilienceConfig": "lexigram.resilience.config",
    "ResilienceModule": "lexigram.resilience.module",
    "ResilienceProvider": "lexigram.resilience.di.provider",
    "TimeoutManager": "lexigram.resilience.timeout.manager",
    # --- Idempotency subsystem (merged from lexigram-idempotency) ---
    "IdempotencyStoreProtocol": "lexigram.contracts.core.idempotency",
    "InMemoryIdempotencyStore": "lexigram.resilience.idempotency.store",
    "idempotent": "lexigram.resilience.decorators",
    "IdempotencyRecord": "lexigram.contracts.domain.idempotency",
    "IdempotencyStatus": "lexigram.contracts.domain.idempotency",
    "IdempotencyResult": "lexigram.resilience.types",
    "DEFAULT_CLEANUP_INTERVAL": "lexigram.resilience.idempotency.constants",
    "DEFAULT_KEY_PREFIX": "lexigram.resilience.idempotency.constants",
    "DEFAULT_MAX_ENTRIES": "lexigram.resilience.idempotency.constants",
    "DEFAULT_MAX_KEY_LENGTH": "lexigram.resilience.idempotency.constants",
    "DEFAULT_TTL": "lexigram.resilience.idempotency.constants",
    "ENV_PREFIX": "lexigram.resilience.constants",
    "IdempotencyConfig": "lexigram.resilience.config",
    "DuplicateRequestError": "lexigram.resilience.exceptions",
    "IdempotencyBackendError": "lexigram.resilience.exceptions",
    "IdempotencyConfigurationError": "lexigram.resilience.exceptions",
    "IdempotencyConflictError": "lexigram.resilience.exceptions",
    "IdempotencyError": "lexigram.resilience.exceptions",
    "IdempotencyStoreError": "lexigram.resilience.exceptions",
    "DatabaseIdempotencyStore": "lexigram.resilience.idempotency.database",
    "RedisIdempotencyStore": "lexigram.resilience.idempotency.redis",
    "IdempotencyMiddleware": "lexigram.resilience.idempotency.middleware",
    "IdempotencyProvider": "lexigram.resilience.idempotency.provider",
    "DurableIdempotencyProvider": "lexigram.resilience.idempotency.durable_provider",
    "IdempotencyModule": "lexigram.resilience.idempotency.module",
    # Hooks
    "CircuitClosedHook": "lexigram.resilience.hooks",
    "CircuitOpenedHook": "lexigram.resilience.hooks",
    "RetryAttemptedHook": "lexigram.resilience.hooks",
    # Events
    "CircuitOpenedEvent": "lexigram.resilience.events",
    "CircuitClosedEvent": "lexigram.resilience.events",
    "RetryExhaustedEvent": "lexigram.resilience.events",
    "IdempotencyKeyHitEvent": "lexigram.resilience.events",
}


def __getattr__(name: str) -> object:
    if name in _LAZY_IMPORTS:
        import importlib

        mod = importlib.import_module(_LAZY_IMPORTS[name])
        value = getattr(mod, name)
        globals()[name] = value
        return value
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(_LAZY_IMPORTS.keys()))


__all__ = list(_LAZY_IMPORTS.keys())
