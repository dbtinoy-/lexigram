"""Domain events for lexigram-ai-rag — immutable facts emitted when pipeline stages complete.

These events are published through EventBusProtocol and consumed by
quality metrics, feedback loops, and audit systems.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from lexigram.contracts.domain.events import DomainEvent

__all__ = [
    "RetrievalCompletedEvent",
    "SynthesisCompletedEvent",
]


@dataclass(frozen=True, init=False)
class RetrievalCompletedEvent(DomainEvent):
    """Emitted when the retrieval stage of a RAG pipeline completes.

    Consumed by: quality metrics, retrieval analytics, feedback loops.
    """

    query_id: str = field(kw_only=True)
    documents_retrieved: int = field(kw_only=True)


@dataclass(frozen=True, init=False)
class SynthesisCompletedEvent(DomainEvent):
    """Emitted when the synthesis stage of a RAG pipeline completes.

    Consumed by: quality metrics, answer analytics, audit.
    """

    query_id: str = field(kw_only=True)
    context_chunks: int = field(kw_only=True)
