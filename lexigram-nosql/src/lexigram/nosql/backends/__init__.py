"""NoSQL backends."""

from __future__ import annotations

from lexigram.nosql.backends.dynamodb.backend import DynamoDBBackend
from lexigram.nosql.backends.firestore.backend import FirestoreBackend

__all__ = ["DynamoDBBackend", "FirestoreBackend"]
