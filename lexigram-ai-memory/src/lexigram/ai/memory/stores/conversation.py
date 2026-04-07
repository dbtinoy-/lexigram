"""Conversation memory store — preserves full interaction history per session."""

from __future__ import annotations

from collections import defaultdict

from lexigram.contracts.ai.memory import MemoryEntry, MemoryQuery, MemorySearchResult
from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)


class ConversationMemoryStore:
    """Stores complete conversation history partitioned by session_id.

    Each session's turns are appended in order. Retrieval returns the
    most recent turns for the requested session (filter via metadata).
    """

    def __init__(self, max_turns_per_session: int = 1000) -> None:
        """Initialise the conversation store.

        Args:
            max_turns_per_session: Maximum turns kept per session.
        """
        self._max = max_turns_per_session
        # session_id → list of entries ordered oldest-first
        self._sessions: dict[str, list[MemoryEntry]] = defaultdict(list)
        self._all: dict[str, MemoryEntry] = {}

    async def store(self, entry: MemoryEntry) -> None:
        """Persist *entry* under its session (from metadata).

        The session is derived from ``entry.metadata["session_id"]`` when
        present, otherwise filed under a ``"_default"`` session.

        Args:
            entry: Memory entry to store.
        """
        session_id: str = entry.metadata.get("session_id", "_default")
        session_turns = self._sessions[session_id]
        session_turns.append(entry)
        if len(session_turns) > self._max:
            evicted = session_turns.pop(0)
            self._all.pop(evicted.id, None)
        self._all[entry.id] = entry

    async def retrieve(self, query: MemoryQuery) -> list[MemorySearchResult]:
        """Return entries for the session specified in *query.filters*.

        Falls back to all entries if no session_id filter is given.

        Args:
            query: Search parameters including optional ``session_id`` filter.

        Returns:
            Most recent entries for the matching session.
        """
        session_id = query.filters.get("session_id")
        if session_id:
            entries = self._sessions.get(session_id, [])
        else:
            entries = list(self._all.values())

        recent = sorted(entries, key=lambda e: e.timestamp, reverse=True)[: query.top_k]
        return [
            MemorySearchResult(entry=e, score=1.0, source="conversation")
            for e in recent
        ]

    async def get_recent(self, n: int) -> list[MemoryEntry]:
        """Return the *n* globally most recent entries.

        Args:
            n: Maximum entries to return.

        Returns:
            Entries ordered newest-first.
        """
        return sorted(self._all.values(), key=lambda e: e.timestamp, reverse=True)[:n]

    async def delete(self, entry_id: str) -> None:
        """Remove entry from all sessions.

        Args:
            entry_id: ID of the entry to remove.
        """
        self._all.pop(entry_id, None)
        for turns in self._sessions.values():
            for i, e in enumerate(turns):
                if e.id == entry_id:
                    turns.pop(i)
                    break

    async def clear(self) -> None:
        """Clear all sessions and entries."""
        self._sessions.clear()
        self._all.clear()

    async def get_session_entries(self, session_id: str) -> list[MemoryEntry]:
        """Return all entries for a given session in chronological order.

        Args:
            session_id: Session identifier.

        Returns:
            Entries in insertion order.
        """
        return list(self._sessions.get(session_id, []))


__all__ = ["ConversationMemoryStore"]
