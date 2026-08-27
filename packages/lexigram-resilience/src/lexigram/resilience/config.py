"""Configuration models for the resilience subsystem.

Contains :class:`ResilienceConfig`, which aggregates circuit-breaker,
retry, bulkhead, and timeout sub-configs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from lexigram.config.base import BaseConfig
from lexigram.contracts.infra.resilience.models import (
    CircuitBreakerConfig,
    RetryConfig,
    TimeoutConfig,
)
from lexigram.domain import DomainModel
from lexigram.resilience import constants as const
from lexigram.validation import ConfigDict, Field


@dataclass(init=False)
class BulkheadConfig(DomainModel):
    """Configuration for bulkhead isolation."""

    max_concurrent: int = Field(default=10, description="Max concurrent requests")
    queue_size: int = Field(default=100, description="Max queue size")
    timeout: float = Field(default=30.0, description="Execution timeout")
    name: str = Field(default="", description="Bulkhead name")


@dataclass(init=False)
class ResilienceConfig(BaseConfig):
    """Circuit breakers, retries, rate limiting, and bulkhead patterns configuration."""

    config_section: ClassVar[str] = "resilience"

    model_config: ClassVar[ConfigDict] = ConfigDict(
        env_prefix=const.ENV_PREFIX,
        env_nested_delimiter=const.ENV_NESTED_DELIMITER,
        extra="ignore",
    )  # type: ignore[typeddict-unknown-key]

    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    # consumed by: CircuitBreaker, CircuitBreakerRegistry
    retry: RetryConfig = field(default_factory=RetryConfig)
    # consumed by: RetryPolicy, retry decorator
    bulkhead: BulkheadConfig = field(default_factory=BulkheadConfig)
    # consumed by: Bulkhead semaphore implementation
    timeout: TimeoutConfig = field(default_factory=TimeoutConfig)
    # consumed by: timeout context manager


__all__ = ["BulkheadConfig", "IdempotencyConfig", "ResilienceConfig"]


# === Idempotency Config (merged from idempotency/config.py) ===

_IDEMPOTENCY_ENV_PREFIX = "LEX_RESILIENCE__IDEMPOTENCY__"
_IDEMPOTENCY_ENV_NESTED_DELIMITER = "__"


@dataclass(init=False)
class IdempotencyConfig(BaseConfig):
    """Idempotency subsystem configuration.

    Controls both in-memory store behaviour (TTL, capacity, cleanup) and
    backing-store key conventions (prefix, max length).

    Attributes:
        ttl: Time-to-live for cached results in seconds.
        max_entries: Maximum number of in-memory entries before FIFO eviction.
        cleanup_interval: Seconds between background expired-record sweeps.
        auto_cleanup: Whether to start the background cleanup task on init.
        key_prefix: Prefix prepended to every key in backing stores (e.g. Redis).
        max_key_length: Maximum allowed length for an idempotency key.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(
        env_prefix=_IDEMPOTENCY_ENV_PREFIX,
        env_nested_delimiter=_IDEMPOTENCY_ENV_NESTED_DELIMITER,
        extra="ignore",
    )  # type: ignore[typeddict-unknown-key]

    ttl: int = Field(
        default=3600, gt=0, description="TTL for cached results in seconds."
    )
    max_entries: int = Field(
        default=10000,
        gt=0,
        description="Maximum in-memory entries before FIFO eviction.",
    )
    cleanup_interval: float = Field(
        default=300.0,
        gt=0,
        description="Seconds between background cleanup sweeps.",
    )
    auto_cleanup: bool = Field(
        default=True, description="Start background cleanup task on init."
    )
    key_prefix: str = Field(
        default="idempotency:", description="Prefix for all keys in backing stores."
    )
    max_key_length: int = Field(
        default=512,
        gt=0,
        description="Maximum allowed idempotency key length.",
    )
