"""Idempotency subsystem for the Lexigram resilience package.

Provides in-memory, Redis-backed, and SQL-backed idempotency stores,
HTTP middleware, DI providers, and a self-contained module.
"""

from __future__ import annotations

from lexigram.resilience.idempotency.constants import (
    DEFAULT_CLEANUP_INTERVAL,
    DEFAULT_KEY_PREFIX,
    DEFAULT_MAX_ENTRIES,
    DEFAULT_MAX_KEY_LENGTH,
    DEFAULT_TTL,
    ENV_NESTED_DELIMITER,
    ENV_PREFIX,
)
from lexigram.resilience.idempotency.database import DatabaseIdempotencyStore
from lexigram.resilience.idempotency.durable_provider import DurableIdempotencyProvider
from lexigram.resilience.idempotency.middleware import IdempotencyMiddleware
from lexigram.resilience.idempotency.module import IdempotencyModule
from lexigram.resilience.idempotency.provider import IdempotencyProvider
from lexigram.resilience.idempotency.redis import RedisIdempotencyStore
from lexigram.resilience.idempotency.store import InMemoryIdempotencyStore

__all__ = [
    "DEFAULT_CLEANUP_INTERVAL",
    "DEFAULT_KEY_PREFIX",
    "DEFAULT_MAX_ENTRIES",
    "DEFAULT_MAX_KEY_LENGTH",
    "DEFAULT_TTL",
    "ENV_NESTED_DELIMITER",
    "ENV_PREFIX",
    "DatabaseIdempotencyStore",
    "DurableIdempotencyProvider",
    "IdempotencyMiddleware",
    "IdempotencyModule",
    "IdempotencyProvider",
    "InMemoryIdempotencyStore",
    "RedisIdempotencyStore",
]
