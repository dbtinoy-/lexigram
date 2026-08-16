"""
MongoDB event store implementation.

This module provides a MongoDB-based event store using motor
for async database access.
"""

from __future__ import annotations

from lexigram.events.stores.mongodb.config import MongoDBConfig
from lexigram.events.stores.mongodb.event_store import MongoDBEventStore
from lexigram.events.stores.mongodb.snapshot_store import MongoDBSnapshotStore
from lexigram.events.stores.mongodb.utils import deserialize_event, serialize_event

__all__ = [
    "MongoDBConfig",
    "MongoDBEventStore",
    "MongoDBSnapshotStore",
    "deserialize_event",
    "serialize_event",
]
