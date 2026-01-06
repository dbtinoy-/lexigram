"""In-memory persistence backend — stores MemoryEntry objects in a dict."""

from __future__ import annotations

from datetime import UTC, datetime
import math

from lexigram.contracts.ai.memory import (
    MemoryEntry,
    MemoryQuery,
    MemorySearchResult,
)
from lexigram.contracts.core import HealthCheckResult, HealthStatus

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def _seconds_since(dt: datetime) -> float:
    """Return elapsed seconds since *dt*."""
    return (datetime.now(UTC) - dt).total_seconds()


def _score(entry: MemoryEntry, query: MemoryQuery) -> float:
    """Compute a weighted relevance score for *entry* against *query*."""
    age_s = _seconds_since(entry.timestamp)
    recency = math.exp(-age_s / 86400.0)
    relevance = 0.5
    return (
        query.recency_weight * recency
        + query.importance_weight * entry.importance
        + query.relevance_weight * relevance
    )


class InMemoryMemoryBackend:
    """MemoryStoreProtocol backed by an in-process dictionary."""

    def __init__(self) -> None:
        self._store: dict[str, MemoryEntry] = {}

    async def store(self, entry: MemoryEntry) -> None:
        self._store[entry.id] = entry

    async def retrieve(self, query: MemoryQuery) -> list[MemorySearchResult]:
        scored: list[tuple[float, MemoryEntry]] = []
        for entry in self._store.values():
            score = _score(entry, query)
            if score < query.min_relevance:
                continue
            if query.time_range:
                start, end = query.time_range
                if not (start <= entry.timestamp <= end):
                    continue
            if query.filters and not all(
                entry.metadata.get(key) == value for key, value in query.filters.items()
            ):
                continue
            scored.append((score, entry))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            MemorySearchResult(entry=entry, score=score, source="in_memory")
            for score, entry in scored[: query.top_k]
        ]

    async def get_recent(self, n: int) -> list[MemoryEntry]:
        sorted_entries = sorted(
            self._store.values(),
            key=lambda entry: entry.timestamp,
            reverse=True,
        )
        return sorted_entries[:n]

    async def delete(self, entry_id: str) -> None:
        self._store.pop(entry_id, None)

    async def clear(self) -> None:
        self._store.clear()

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        return HealthCheckResult(
            component="memory.in_memory",
            status=HealthStatus.HEALTHY,
            details={"entries": len(self._store), "timeout": timeout},
        )

    def __len__(self) -> int:
        return len(self._store)


__all__ = ["InMemoryMemoryBackend"]
