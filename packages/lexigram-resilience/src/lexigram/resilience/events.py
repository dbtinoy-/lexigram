"""Domain events for resilience subsystem."""

from __future__ import annotations

from dataclasses import dataclass

from lexigram.contracts.domain.events import DomainEvent


@dataclass(frozen=True, init=False)
class CircuitOpenedEvent(DomainEvent):
    """Circuit breaker opened due to threshold breach."""

    service_name: str
    failure_count: int


@dataclass(frozen=True, init=False)
class CircuitClosedEvent(DomainEvent):
    """Circuit breaker closed and restored to normal operation."""

    service_name: str


@dataclass(frozen=True, init=False)
class RetryExhaustedEvent(DomainEvent):
    """Retry strategy exhausted all attempts."""

    service_name: str
    operation: str
    attempt_count: int


@dataclass(frozen=True, init=False)
class IdempotencyKeyHitEvent(DomainEvent):
    """Idempotency key cache hit detected."""

    key: str
    operation: str
