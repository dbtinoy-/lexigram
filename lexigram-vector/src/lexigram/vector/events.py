from __future__ import annotations

from dataclasses import dataclass

from lexigram.contracts.domain.events import DomainEvent


@dataclass(frozen=True, init=False)
class VectorIndexedEvent(DomainEvent):
    """Raised when a document is successfully indexed into a vector store.

    Downstream: observability, audit logging.
    """

    collection: str
    document_id: str


@dataclass(frozen=True, init=False)
class VectorSearchedEvent(DomainEvent):
    """Raised when a similarity search is performed against a vector collection.

    Downstream: analytics, quota tracking.
    """

    collection: str
    result_count: int


@dataclass(frozen=True, init=False)
class VectorDeletedEvent(DomainEvent):
    """Raised when a document is removed from a vector store.

    Downstream: audit logging, cache invalidation.
    """

    collection: str
    document_id: str
