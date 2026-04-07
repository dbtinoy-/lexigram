"""Domain events for NoSQL operations."""

from __future__ import annotations

from dataclasses import dataclass

from lexigram.contracts.domain.events import DomainEvent


@dataclass(frozen=True, init=False)
class MigrationAppliedEvent(DomainEvent):
    """Migration was applied successfully."""

    migration_name: str
    database: str


@dataclass(frozen=True, init=False)
class MigrationFailedEvent(DomainEvent):
    """Migration failed."""

    migration_name: str
    database: str
    error: str


@dataclass(frozen=True, init=False)
class NoSQLConnectedEvent(DomainEvent):
    """NoSQL database connected."""

    database: str
    host: str


@dataclass(frozen=True, init=False)
class NoSQLDisconnectedEvent(DomainEvent):
    """NoSQL database disconnected."""

    database: str
