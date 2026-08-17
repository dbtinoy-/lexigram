"""Database-backed memory backend — persists entries via DatabaseProviderProtocol."""

from __future__ import annotations

from datetime import UTC, datetime
import math
from typing import TYPE_CHECKING, Any, cast

from lexigram.contracts.ai.memory import (
    MemoryEntry,
    MemoryQuery,
    MemorySearchResult,
)
from lexigram.contracts.core import HealthCheckResult, HealthStatus
from lexigram.serialization.backends.json import dumps_str, loads

if TYPE_CHECKING:
    from lexigram.contracts.data import DatabaseProviderProtocol

_SELECT_ALL = (
    "SELECT id, owner_id, content, role, timestamp, importance, metadata, embedding"
    " FROM memory_entries WHERE owner_id = $1"
)
_INSERT = (
    "INSERT INTO memory_entries (id, owner_id, content, role, timestamp, importance, metadata, embedding)"
    " VALUES ($1,$2,$3,$4,$5,$6,$7,$8)"
    " ON CONFLICT (id) DO UPDATE SET content=EXCLUDED.content, importance=EXCLUDED.importance"
)
_DELETE = "DELETE FROM memory_entries WHERE id = $1 AND owner_id = $2"
_CLEAR = "DELETE FROM memory_entries WHERE owner_id = $1"
_RECENT = f"{_SELECT_ALL} ORDER BY timestamp DESC LIMIT $2"


def _normalise_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value)
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
    raise ValueError(f"Unsupported timestamp value type: {type(value).__name__}")


def _row_to_entry(row: dict[str, Any]) -> MemoryEntry:
    metadata_raw = row.get("metadata") or {}
    metadata: dict[str, Any]
    if isinstance(metadata_raw, str):
        metadata = cast("dict[str, Any]", loads(metadata_raw))
    else:
        metadata = cast("dict[str, Any]", metadata_raw)

    embedding_raw = row.get("embedding")
    embedding = cast(
        "list[float] | None", list(embedding_raw) if embedding_raw else None
    )

    return MemoryEntry(
        id=str(row["id"]),
        owner_id=str(row["owner_id"]),
        content=str(row["content"]),
        role=str(row["role"]),
        timestamp=_normalise_timestamp(row["timestamp"]),
        importance=float(row.get("importance", 0.5)),
        metadata=metadata,
        embedding=embedding,
    )


class DatabaseMemoryBackend:
    """MemoryStoreProtocol backed by an SQL database."""

    def __init__(self, provider: DatabaseProviderProtocol) -> None:
        self._provider = provider

    async def store(self, entry: MemoryEntry) -> None:
        async with self._provider.scoped_context():
            conn = await self._provider.get_scoped_connection()
            await conn.execute(
                _INSERT,
                [
                    entry.id,
                    entry.owner_id,
                    entry.content,
                    entry.role,
                    entry.timestamp,
                    entry.importance,
                    dumps_str(entry.metadata),
                    entry.embedding,
                ],
            )

    async def retrieve(self, query: MemoryQuery) -> list[MemorySearchResult]:
        async with self._provider.scoped_context():
            conn = await self._provider.get_scoped_connection()
            query_result = await conn.execute(_SELECT_ALL, [query.owner_id])

        entries = [_row_to_entry(row) for row in query_result.rows]
        scored: list[tuple[float, MemoryEntry]] = []
        for entry in entries:
            age_seconds = (datetime.now(UTC) - entry.timestamp).total_seconds()
            recency = math.exp(-age_seconds / 86400.0)
            score = (
                query.recency_weight * recency
                + query.importance_weight * entry.importance
                + query.relevance_weight * 0.5
            )
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
            MemorySearchResult(entry=entry, score=score, source="database")
            for score, entry in scored[: query.top_k]
        ]

    async def get_recent(self, n: int, owner_id: str) -> list[MemoryEntry]:
        async with self._provider.scoped_context():
            conn = await self._provider.get_scoped_connection()
            query_result = await conn.execute(_RECENT, [owner_id, n])
        return [_row_to_entry(row) for row in query_result.rows]

    async def delete(self, entry_id: str, owner_id: str) -> None:
        async with self._provider.scoped_context():
            conn = await self._provider.get_scoped_connection()
            await conn.execute(_DELETE, [entry_id, owner_id])

    async def clear(self, owner_id: str) -> None:
        async with self._provider.scoped_context():
            conn = await self._provider.get_scoped_connection()
            await conn.execute(_CLEAR, [owner_id])

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        provider_result = await self._provider.health_check(timeout=timeout)
        status = (
            HealthStatus.HEALTHY
            if provider_result.is_healthy()
            else HealthStatus.DEGRADED
        )
        return HealthCheckResult(
            component="memory.database",
            status=status,
            message=provider_result.message,
            error=provider_result.error,
            details={"timeout": timeout},
        )


__all__ = ["DatabaseMemoryBackend"]
