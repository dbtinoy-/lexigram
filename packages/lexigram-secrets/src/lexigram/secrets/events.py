"""Domain events for the secrets/credential vault subsystem."""

from __future__ import annotations

from dataclasses import dataclass

from lexigram.contracts.domain.events import DomainEvent

__all__ = [
    "SecretAccessedEvent",
    "SecretCreatedEvent",
    "SecretDeletedEvent",
    "SecretRotatedEvent",
]


@dataclass(frozen=True)
class SecretCreatedEvent(DomainEvent):
    """A new secret was stored."""

    key: str


@dataclass(frozen=True)
class SecretRotatedEvent(DomainEvent):
    """A secret was rotated to a new version."""

    key: str
    new_version: int


@dataclass(frozen=True)
class SecretDeletedEvent(DomainEvent):
    """A secret was deleted."""

    key: str


@dataclass(frozen=True)
class SecretAccessedEvent(DomainEvent):
    """A secret value was read."""

    key: str
