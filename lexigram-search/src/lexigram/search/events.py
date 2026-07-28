"""Root event surface for lexigram-search.

Defines domain events emitted by the search subsystem (indexing and
query execution).  Consumers subscribe via
:class:`~lexigram.contracts.events.protocols.EventBusProtocol`.
"""

from __future__ import annotations

from dataclasses import dataclass

from lexigram.contracts.domain.events import DomainEvent

__all__ = [
    "IndexingCompletedEvent",
    "SearchExecutedEvent",
]


@dataclass(frozen=True, kw_only=True)
class IndexingCompletedEvent(DomainEvent):
    """Emitted when a batch indexing operation finishes.

    Attributes:
        index_name: Name of the search index that was updated.
        documents_indexed: Number of documents successfully indexed.
    """

    index_name: str
    documents_indexed: int = 0


@dataclass(frozen=True, kw_only=True)
class SearchExecutedEvent(DomainEvent):
    """Emitted when a search query is executed against the engine.

    Attributes:
        index_name: Name of the index that was searched.
        query: The search query string.
        result_count: Number of results returned.
    """

    index_name: str
    query: str
    result_count: int = 0
