"""Root hook payload surface for lexigram-ai-memory.

Defines canonical payload dataclasses for memory-tier lifecycle hook points.
Actual hook registration and invocation use the framework's string-keyed
``HookRegistryProtocol`` action/filter APIs.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "MemoryConsolidatedHook",
    "MemoryRetrievedHook",
    "MemoryWrittenHook",
]


@dataclass(frozen=True, kw_only=True)
class MemoryWrittenHook:
    """Payload fired when an entry is written to a memory store.

    Attributes:
        tier: Memory tier that received the write (e.g. ``"working"``,
            ``"episodic"``, or ``"semantic"``).
        backend: Backend identifier that persisted the entry (e.g.
            ``"in_memory"`` or ``"vector"``).
    """

    tier: str
    backend: str


@dataclass(frozen=True, kw_only=True)
class MemoryRetrievedHook:
    """Payload fired when entries are retrieved from a memory store.

    Attributes:
        tier: Memory tier that was queried.
        result_count: Number of entries returned by the retrieval.
    """

    tier: str
    result_count: int


@dataclass(frozen=True, kw_only=True)
class MemoryConsolidatedHook:
    """Payload fired after a memory consolidation pass completes.

    Attributes:
        strategy: Name of the consolidation strategy that ran (e.g.
            ``"recency_decay"`` or ``"deduplication"``).
    """

    strategy: str
