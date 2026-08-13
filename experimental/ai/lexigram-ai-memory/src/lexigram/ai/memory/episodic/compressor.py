"""Episodic memory compressor — summarises old entries to reclaim context space."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.ai.memory.exceptions import ConsolidationError
from lexigram.contracts.ai.memory import MemoryEntry
from lexigram.logging import (
    get_logger,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

logger = get_logger(__name__)


class EpisodicCompressor:
    """Compresses episodic memory entries by LLM-assisted summarisation.

    When the episodic store grows beyond a threshold, older entries are
    grouped by session and collapsed into a single summary entry.
    """

    def __init__(
        self,
        summarise_fn: Callable[[list[MemoryEntry]], Awaitable[MemoryEntry]]
        | None = None,
    ) -> None:
        """Initialise the compressor.

        Args:
            summarise_fn: Async callable that accepts a list of entries and
                returns a single summary entry. When *None*, a simple
                concatenation fallback is used.
        """
        self._summarise_fn = summarise_fn

    async def compress(
        self,
        entries: list[MemoryEntry],
        *,
        max_tokens: int = 200,
    ) -> MemoryEntry:
        """Compress *entries* into a single condensed memory entry.

        Args:
            entries: Chronologically ordered entries to compress.
            max_tokens: Hint to the summariser for output length.

        Returns:
            A new MemoryEntry representing the compressed form.

        Raises:
            ConsolidationError: If the summarisation callable raises.
        """
        if not entries:
            raise ConsolidationError("Cannot compress an empty list of entries")

        if self._summarise_fn:
            try:
                return await self._summarise_fn(entries)
            except (RuntimeError, ValueError, TypeError) as exc:
                raise ConsolidationError(
                    "Summarisation failed during compression"
                ) from exc

        return self._concatenate_fallback(entries)

    def _concatenate_fallback(self, entries: list[MemoryEntry]) -> MemoryEntry:
        """Produce a naive concatenation summary when no LLM is configured."""
        from datetime import UTC, datetime
        from uuid import uuid4

        combined = " | ".join(e.content[:100] for e in entries)
        avg_importance = sum(e.importance for e in entries) / len(entries)
        return MemoryEntry(
            id=str(uuid4()),
            owner_id=entries[0].owner_id,
            content=f"[summary of {len(entries)} turns] {combined}",
            role="system",
            timestamp=datetime.now(UTC),
            importance=avg_importance,
            metadata={"compressed_ids": [e.id for e in entries], "type": "summary"},
        )


# Avoid circular import for type hints

__all__ = ["EpisodicCompressor"]
