"""Domain events for lexigram-ai-memory — immutable facts emitted when memory operations occur.

These events are published through EventBusProtocol and consumed by
AI audit trails, context management, and safety review systems.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from lexigram.contracts.domain.events import DomainEvent

__all__ = [
    "MemoryRetrievedEvent",
    "MemoryStoredEvent",
]


@dataclass(frozen=True, init=False)
class MemoryStoredEvent(DomainEvent):
    """Emitted when a memory entry is persisted to the memory store.

    Consumed by: AI audit trails, context management, safety review.
    """

    memory_id: str
    memory_type: str
    occurred_at: datetime = field(
        default_factory=lambda: datetime.now(UTC), kw_only=True
    )


@dataclass(frozen=True, init=False)
class MemoryRetrievedEvent(DomainEvent):
    """Emitted when a memory query returns results.

    Consumed by: AI audit trails, context relevance analytics.
    """

    query_id: str
    results_count: int
    occurred_at: datetime = field(
        default_factory=lambda: datetime.now(UTC), kw_only=True
    )
