"""Entity memory store — tracks named-entity mentions across turns."""

from __future__ import annotations

from collections import defaultdict

from lexigram.contracts.ai.memory import MemoryEntry, MemoryQuery, MemorySearchResult
from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)


class EntityMemoryStore:
    """Indexes memory entries by the entities they mention.

    Entries are stored normally but also indexed by lowercase entity token
    so that entity-scoped retrieval is O(1) per entity.
    """

    def __init__(self) -> None:
        """Initialise the entity store."""
        self._entries: dict[str, MemoryEntry] = {}
        self._entity_index: dict[str, set[str]] = defaultdict(set)

    async def store(
        self, entry: MemoryEntry, entities: list[str] | None = None
    ) -> None:
        """Store *entry* and index it under each entity in *entities*.

        Args:
            entry: Memory entry to persist.
            entities: Entity names to associate with this entry.
        """
        self._entries[entry.id] = entry
        for entity in entities or []:
            self._entity_index[entity.lower()].add(entry.id)

    async def retrieve(self, query: MemoryQuery) -> list[MemorySearchResult]:
        """Return entries scored by importance.

        Args:
            query: Search parameters.

        Returns:
            Top-k entries ranked by importance.
        """
        scored = sorted(
            self._entries.values(),
            key=lambda e: e.importance,
            reverse=True,
        )
        return [
            MemorySearchResult(entry=e, score=e.importance, source="entity")
            for e in scored[: query.top_k]
        ]

    async def get_recent(self, n: int) -> list[MemoryEntry]:
        """Return the *n* most recent entries.

        Args:
            n: Maximum entries to return.

        Returns:
            Entries ordered newest-first.
        """
        return sorted(
            self._entries.values(),
            key=lambda e: e.timestamp,
            reverse=True,
        )[:n]

    async def delete(self, entry_id: str) -> None:
        """Remove entry and its entity index entries.

        Args:
            entry_id: ID of the entry to remove.
        """
        self._entries.pop(entry_id, None)
        for ids in self._entity_index.values():
            ids.discard(entry_id)

    async def clear(self) -> None:
        """Remove all entries and entity index data."""
        self._entries.clear()
        self._entity_index.clear()

    async def get_by_entity(self, entity: str) -> list[MemoryEntry]:
        """Return all entries mentioning *entity*.

        Args:
            entity: Entity name to search.

        Returns:
            Entries referencing the entity, newest-first.
        """
        ids = self._entity_index.get(entity.lower(), set())
        entries = [self._entries[eid] for eid in ids if eid in self._entries]
        return sorted(entries, key=lambda e: e.timestamp, reverse=True)


__all__ = ["EntityMemoryStore"]
