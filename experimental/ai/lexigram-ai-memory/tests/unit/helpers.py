"""Test helper factories for lexigram-ai-memory unit tests.

These are plain functions (not fixtures) — import directly in test files.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from lexigram.contracts.ai.memory import MemoryEntry, MemoryQuery


def make_entry(
    content: str = "test content",
    role: str = "user",
    importance: float = 0.5,
    metadata: dict | None = None,
    owner_id: str = "owner-1",
) -> MemoryEntry:
    """Create a MemoryEntry with a fresh UUID and current timestamp."""
    return MemoryEntry(
        id=str(uuid4()),
        owner_id=owner_id,
        content=content,
        role=role,
        timestamp=datetime.now(UTC),
        importance=importance,
        metadata=metadata or {},
    )


def make_query(
    query: str = "test query",
    top_k: int = 10,
    min_relevance: float = 0.0,
    owner_id: str = "owner-1",
) -> MemoryQuery:
    """Create a standard MemoryQuery."""
    return MemoryQuery(
        owner_id=owner_id, query=query, top_k=top_k, min_relevance=min_relevance
    )
