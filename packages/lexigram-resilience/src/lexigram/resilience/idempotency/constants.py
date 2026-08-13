"""Idempotency subsystem constants.

These constants are used by IdempotencyConfig and the idempotency stores.
"""

from __future__ import annotations

ENV_PREFIX: str = "LEX_RESILIENCE__IDEMPOTENCY__"
"""Environment variable prefix for idempotency configuration."""

ENV_NESTED_DELIMITER: str = "__"
"""Nested delimiter for environment variable configuration."""

DEFAULT_TTL: int = 3600
"""Default time-to-live for cached results in seconds."""

DEFAULT_MAX_ENTRIES: int = 10_000
"""Default maximum number of in-memory entries before FIFO eviction."""

DEFAULT_CLEANUP_INTERVAL: float = 300.0
"""Default seconds between background cleanup sweeps."""

DEFAULT_KEY_PREFIX: str = "idempotency:"
"""Default prefix for all keys in backing stores."""

DEFAULT_MAX_KEY_LENGTH: int = 512
"""Default maximum allowed idempotency key length."""

__all__ = [
    "DEFAULT_CLEANUP_INTERVAL",
    "DEFAULT_KEY_PREFIX",
    "DEFAULT_MAX_ENTRIES",
    "DEFAULT_MAX_KEY_LENGTH",
    "DEFAULT_TTL",
    "ENV_NESTED_DELIMITER",
    "ENV_PREFIX",
]
