"""DynamoDB document store backend for lexigram-nosql."""

from __future__ import annotations

from lexigram.nosql.backends.dynamodb.backend import DynamoDBBackend
from lexigram.nosql.backends.dynamodb.collection import DynamoDBCollection

__all__ = ["DynamoDBBackend", "DynamoDBCollection"]
