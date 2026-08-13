"""MongoDB backend for lexigram-nosql."""

from __future__ import annotations

from lexigram.nosql.backends.mongodb.backend import MongoDBDocumentStore
from lexigram.nosql.backends.mongodb.collection import MongoDBCollection

__all__ = ["MongoDBCollection", "MongoDBDocumentStore"]
