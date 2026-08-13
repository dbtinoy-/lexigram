"""Aggregates module for Domain-Driven Design.

This module provides:
- AggregateRoot: Base class for event-sourced aggregates
- Entity: Base class for entities within aggregates
- ValueObject: Base class for immutable value objects
"""

from __future__ import annotations

from lexigram.events.aggregates.aggregate import AggregateRoot, VersionedAggregateRoot
from lexigram.events.aggregates.entity import Entity, VersionedEntity
from lexigram.events.aggregates.value_object import SingleValueObject, ValueObject

__all__ = [
    "AggregateRoot",
    "Entity",
    "SingleValueObject",
    "ValueObject",
    "VersionedAggregateRoot",
    "VersionedEntity",
]
