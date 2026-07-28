"""Summary memory store — compresses old turns via LLM-assisted summarisation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.ai.memory.exceptions import ConsolidationError
from lexigram.ai.memory.stores.buffer import BufferMemoryStore
from lexigram.contracts.ai.memory import MemoryEntry, MemoryQuery, MemorySearchResult
from lexigram.logging import (
    get_logger,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

logger = get_logger(__name__)


class SummaryMemoryStore:
    """Memory store that periodically compresses older turns into summaries.

    Maintains a hot buffer of recent turns and a list of compressed summary
    entries. When the hot buffer exceeds *compress_threshold*, the oldest
    *compress_batch* entries are collapsed via *summarise_fn*.
    """

    def __init__(
        self,
        compress_threshold: int = 20,
        compress_batch: int = 10,
        summarise_fn: Callable[[list[MemoryEntry]], Awaitable[MemoryEntry]]
        | None = None,
    ) -> None:
        """Initialise the summary store.

        Args:
            compress_threshold: Number of hot entries that triggers compression.
            compress_batch: Number of oldest entries to compress per run.
            summarise_fn: Async callable that reduces a batch to one entry.
        """
        self._threshold = compress_threshold
        self._batch = compress_batch
        self._summarise_fn = summarise_fn
        self._hot: BufferMemoryStore = BufferMemoryStore(
            max_entries=compress_threshold * 2
        )
        self._summaries: list[MemoryEntry] = []

    async def store(self, entry: MemoryEntry) -> None:
        """Add *entry* to the hot buffer, compressing if necessary.

        Args:
            entry: Memory entry to add.
        """
        await self._hot.store(entry)
        hot_entries = await self._hot.get_recent(self._threshold * 2)
        if len(hot_entries) >= self._threshold:
            await self._maybe_compress(hot_entries)

    async def retrieve(self, query: MemoryQuery) -> list[MemorySearchResult]:
        """Return summaries plus most recent hot entries.

        Args:
            query: Search parameters.

        Returns:
            Combined results from summaries and hot buffer.
        """
        results: list[MemorySearchResult] = [
            MemorySearchResult(entry=s, score=0.9, source="summary")
            for s in self._summaries[-(query.top_k // 2) :]
        ]
        hot_results = await self._hot.retrieve(query)
        results.extend(hot_results)
        return results[: query.top_k]

    async def get_recent(self, n: int) -> list[MemoryEntry]:
        """Return the *n* most recent entries (hot buffer only).

        Args:
            n: Maximum entries to return.

        Returns:
            Most recent entries, newest-first.
        """
        return await self._hot.get_recent(n)

    async def delete(self, entry_id: str) -> None:
        """Remove entry with *entry_id* from hot buffer or summaries.

        Args:
            entry_id: ID of the entry to remove.
        """
        await self._hot.delete(entry_id)
        self._summaries = [s for s in self._summaries if s.id != entry_id]

    async def clear(self) -> None:
        """Clear all hot entries and summaries."""
        await self._hot.clear()
        self._summaries.clear()

    async def _maybe_compress(self, hot_entries: list[MemoryEntry]) -> None:
        """Compress the oldest batch of hot entries into a summary."""
        oldest = list(reversed(hot_entries))[: self._batch]
        if not oldest:
            return
        try:
            if self._summarise_fn:
                summary = await self._summarise_fn(oldest)
            else:
                summary = self._fallback_summary(oldest)
        except (RuntimeError, ValueError, TypeError) as exc:
            raise ConsolidationError("Summary compression failed") from exc

        for entry in oldest:
            await self._hot.delete(entry.id)
        self._summaries.append(summary)
        logger.debug("summary_compressed", entries=len(oldest))

    def _fallback_summary(self, entries: list[MemoryEntry]) -> MemoryEntry:
        from datetime import UTC, datetime
        from uuid import uuid4

        combined = " | ".join(e.content[:80] for e in entries)
        avg_imp = sum(e.importance for e in entries) / len(entries)
        return MemoryEntry(
            id=str(uuid4()),
            content=f"[summary:{len(entries)} turns] {combined}",
            role="system",
            timestamp=datetime.now(UTC),
            importance=avg_imp,
            metadata={"compressed_ids": [e.id for e in entries], "type": "summary"},
        )


__all__ = ["SummaryMemoryStore"]
