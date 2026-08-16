"""Constants for the resilience subsystem.

Typed defaults for retry, circuit-breaker, bulkhead, and timeout policies.
"""

from __future__ import annotations

import importlib.metadata

# -- Version -------------------------------------------------------------------

try:
    __version__: str = importlib.metadata.version("lexigram-resilience")
except ImportError:
    __version__ = "0.0.0"

# -- Environment Variable Prefix -------------------------------------------

ENV_PREFIX: str = "LEX_RESILIENCE__"
"""Environment variable prefix for resilience configuration."""

ENV_NESTED_DELIMITER: str = "__"
"""Nested delimiter for environment variable configuration."""


# -- Retry Policy Defaults -------------------------------------------------

DEFAULT_RETRY_ATTEMPTS: int = 3
"""Default maximum retry attempts; consumed by: RetryPolicy, RetryConfig."""

DEFAULT_RETRY_DELAY: float = 1.0
"""Default initial delay between retries in seconds; consumed by: RetryPolicy."""

# -- Circuit Breaker Defaults ----------------------------------------------

DEFAULT_CB_FAILURE_THRESHOLD: int = 5
"""Failures before the circuit opens; consumed by: CircuitBreakerConfig."""

DEFAULT_CB_RECOVERY_TIMEOUT: float = 60.0
"""Seconds in OPEN state before moving to HALF-OPEN; consumed by: CircuitBreakerConfig."""

# -- Bulkhead Defaults -----------------------------------------------------

DEFAULT_BULKHEAD_MAX_CONCURRENT: int = 10
"""Maximum concurrent executions allowed; consumed by: BulkheadConfig."""

# -- Rate Limiter Defaults -------------------------------------------------

DEFAULT_RATE_LIMIT_WINDOW: float = 60.0
"""Sliding window duration in seconds for rate limiting; consumed by: CanonicalRateLimiter."""

# -- Timeout Defaults ------------------------------------------------------

DEFAULT_TIMEOUT: float = 30.0
"""Default operation timeout in seconds; consumed by: TimeoutConfig."""

__all__ = [
    "DEFAULT_BULKHEAD_MAX_CONCURRENT",
    "DEFAULT_CB_FAILURE_THRESHOLD",
    "DEFAULT_CB_RECOVERY_TIMEOUT",
    "DEFAULT_CLEANUP_INTERVAL",
    "DEFAULT_KEY_PREFIX",
    "DEFAULT_MAX_ENTRIES",
    "DEFAULT_MAX_KEY_LENGTH",
    "DEFAULT_RATE_LIMIT_WINDOW",
    "DEFAULT_RETRY_ATTEMPTS",
    "DEFAULT_RETRY_DELAY",
    "DEFAULT_TTL",
    "DEFAULT_TIMEOUT",
    "ENV_NESTED_DELIMITER",
    "ENV_PREFIX",
]


# === Idempotency Constants (merged from idempotency/constants.py) ===
DEFAULT_CLEANUP_INTERVAL: float = 300.0
DEFAULT_KEY_PREFIX: str = "idempotency:"
DEFAULT_MAX_ENTRIES: int = 10000
DEFAULT_MAX_KEY_LENGTH: int = 256
DEFAULT_TTL: int = 3600
