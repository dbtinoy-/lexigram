"""Buffer memory store — FIFO sliding window over raw MemoryEntry objects."""

from __future__ import annotations

from collections import deque

from lexigram.contracts.ai.memory import MemoryEntry, MemoryQuery, MemorySearchResult
from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)


class BufferMemoryStore:
    """Fixed-capacity FIFO buffer of raw conversation turns.

    The oldest entries are evicted when the buffer reaches *max_entries*.
    """

    def __init__(self, max_entries: int = 100) -> None:
        """Initialise the buffer.

        Args:
            max_entries: Maximum number of entries to retain.
        """
        self._max = max_entries
        self._buffer: deque[MemoryEntry] = deque(maxlen=max_entries)

    async def store(self, entry: MemoryEntry) -> None:
        """Append *entry* to the buffer, evicting the oldest if full.

        Args:
            entry: Memory entry to store.
        """
        self._buffer.append(entry)

    async def retrieve(self, query: MemoryQuery) -> list[MemorySearchResult]:
        """Return the *top_k* most recent entries as search results.

        Args:
            query: Search parameters (only top_k is used).

        Returns:
            Most recent entries wrapped in search results with score 1.0.
        """
        recent = list(reversed(self._buffer))[: query.top_k]
        return [MemorySearchResult(entry=e, score=1.0, source="buffer") for e in recent]

    async def get_recent(self, n: int) -> list[MemoryEntry]:
        """Return the *n* most recent entries.

        Args:
            n: Maximum entries to return.

        Returns:
            Entries ordered newest-first.
        """
        return list(reversed(self._buffer))[:n]

    async def delete(self, entry_id: str) -> None:
        """Remove entry with *entry_id* from the buffer.

        Args:
            entry_id: ID of the entry to remove.
        """
        to_keep = [e for e in self._buffer if e.id != entry_id]
        self._buffer.clear()
        self._buffer.extend(to_keep)

    async def clear(self) -> None:
        """Clear all entries from the buffer."""
        self._buffer.clear()

    def __len__(self) -> int:
        return len(self._buffer)


__all__ = ["BufferMemoryStore"]
