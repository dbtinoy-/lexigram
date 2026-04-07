from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from lexigram.contracts.ai.memory import MemoryEntry


@runtime_checkable
class MemoryIndexProtocol(Protocol):
    """Indexes and retrieves memory entries by semantic similarity."""

    async def index(self, entry: MemoryEntry) -> str:
        """Index a memory entry and return its ID."""
        ...

    async def search(self, query: str, top_k: int) -> list[MemoryEntry]: ...


@runtime_checkable
class ConsolidationStrategyProtocol(Protocol):
    """Strategy for consolidating episodic memories into semantic memories."""

    async def consolidate(self, entries: list[MemoryEntry]) -> list[MemoryEntry]: ...
