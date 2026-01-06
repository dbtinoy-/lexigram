"""ConversationBuffer — simple FIFO working memory strategy.

Maintains the most recent N conversation turns in memory, evicting oldest
entries when limits are exceeded. Useful as a lightweight context window
strategy when full episodic/semantic recall is not needed.
"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

from lexigram.logging import (
    get_logger,
)

if TYPE_CHECKING:
    from lexigram.contracts.ai.memory import MemoryEntry

logger = get_logger(__name__)


class ConversationBuffer:
    """FIFO buffer that keeps the most recent conversation turns.

    Provides a simple, bounded working-memory strategy that auto-evicts
    the oldest entries when ``max_turns`` or ``max_tokens`` limits are hit.

    Example::

        buffer = ConversationBuffer(max_turns=20, max_tokens=4096)
        await buffer.add(entry)
        context = buffer.get_context()

    Args:
        max_turns: Maximum number of turns to retain.
        max_tokens: Soft token cap — oldest entries are evicted until the
            total estimated token count is at or below this limit.
            Set to 0 to disable token-based eviction.
    """

    def __init__(
        self,
        max_turns: int = 20,
        max_tokens: int = 4096,
    ) -> None:
        """Initialise the conversation buffer.

        Args:
            max_turns: Maximum number of turns to retain.
            max_tokens: Soft token cap (0 = no token limit).
        """
        self._max_turns = max_turns
        self._max_tokens = max_tokens
        self._entries: deque[MemoryEntry] = deque(maxlen=max_turns)
        self._total_tokens: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def add(self, entry: MemoryEntry) -> None:
        """Add a memory entry to the buffer.

        If adding the entry would exceed ``max_turns``, the oldest entry
        is automatically evicted. After insertion, token-based eviction
        is applied if ``max_tokens > 0``.

        Args:
            entry: The memory entry to add.
        """
        tokens = self._estimate_tokens(entry)

        # If deque is at capacity, account for the evicted entry
        if len(self._entries) == self._max_turns:
            evicted = self._entries[0]
            self._total_tokens -= self._estimate_tokens(evicted)

        self._entries.append(entry)
        self._total_tokens += tokens

        # Token-based eviction
        if self._max_tokens > 0:
            while self._total_tokens > self._max_tokens and len(self._entries) > 1:
                evicted = self._entries.popleft()
                self._total_tokens -= self._estimate_tokens(evicted)

        logger.debug(
            "buffer_add",
            entry_id=entry.id,
            buffer_size=len(self._entries),
            total_tokens=self._total_tokens,
        )

    def get_context(self) -> list[MemoryEntry]:
        """Return all entries currently in the buffer, oldest-first.

        Returns:
            Ordered list of memory entries.
        """
        return list(self._entries)

    def clear(self) -> None:
        """Remove all entries from the buffer."""
        self._entries.clear()
        self._total_tokens = 0

    @property
    def size(self) -> int:
        """Number of entries currently in the buffer."""
        return len(self._entries)

    @property
    def total_tokens(self) -> int:
        """Estimated total token count across all buffered entries."""
        return self._total_tokens

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _estimate_tokens(entry: MemoryEntry) -> int:
        """Rough token estimate: ~4 chars per token.

        Args:
            entry: Memory entry.

        Returns:
            Estimated token count.
        """
        return max(1, len(entry.content) // 4)

    def __len__(self) -> int:
        """Number of entries in the buffer."""
        return len(self._entries)

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"ConversationBuffer(size={len(self._entries)}, "
            f"max_turns={self._max_turns}, "
            f"tokens={self._total_tokens}/{self._max_tokens})"
        )


__all__ = ["ConversationBuffer"]
