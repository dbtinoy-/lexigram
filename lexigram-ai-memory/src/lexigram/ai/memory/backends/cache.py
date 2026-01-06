"""Cache-backed memory backend — persists entries via CacheBackendProtocol."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

from lexigram.ai.memory.exceptions import MemoryStoreError
from lexigram.contracts.ai.memory import (
    MemoryEntry,
    MemoryQuery,
    MemorySearchResult,
)
from lexigram.contracts.core import HealthCheckResult, HealthStatus
from lexigram.serialization.backends.json import dumps_str, loads

if TYPE_CHECKING:
    from lexigram.contracts.infra.cache import CacheBackendProtocol

_KEY_PREFIX = "mem:"
_INDEX_KEY = "mem:index"


class CacheMemoryBackend:
    """MemoryStoreProtocol backed by a CacheBackendProtocol (e.g. Redis)."""

    def __init__(self, cache: CacheBackendProtocol, ttl: int = 86400 * 30) -> None:
        self._cache = cache
        self._ttl = ttl

    def _key(self, entry_id: str) -> str:
        return f"{_KEY_PREFIX}{entry_id}"

    def _to_json(self, entry: MemoryEntry) -> str:
        payload = {
            "id": entry.id,
            "content": entry.content,
            "role": entry.role,
            "timestamp": entry.timestamp.isoformat(),
            "importance": entry.importance,
            "metadata": entry.metadata,
            "embedding": entry.embedding,
        }
        return dumps_str(payload)

    def _from_json(self, raw: str) -> MemoryEntry:
        data = cast("dict[str, Any]", loads(raw))
        return MemoryEntry(
            id=str(data["id"]),
            content=str(data["content"]),
            role=str(data["role"]),
            timestamp=datetime.fromisoformat(str(data["timestamp"])),
            importance=float(data.get("importance", 0.5)),
            metadata=cast("dict[str, Any]", data.get("metadata", {})),
            embedding=cast("list[float] | None", data.get("embedding")),
        )

    def _as_json_text(self, value: Any | None) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, bytes):
            return value.decode("utf-8")
        raise MemoryStoreError(
            "Cache value was not JSON-serializable text", store="cache"
        )

    async def _cache_get_text(self, key: str) -> str | None:
        get_result = await self._cache.get(key)
        if get_result.is_err():
            raise MemoryStoreError(
                f"Cache get failed for key {key}",
                store="cache",
            ) from get_result.unwrap_err()
        return self._as_json_text(get_result.unwrap_or(None))

    async def _cache_set_text(
        self, key: str, value: str, ttl: int | None = None
    ) -> None:
        set_result = await self._cache.set(key, value, ttl=ttl)
        if set_result.is_err():
            raise MemoryStoreError(
                f"Cache set failed for key {key}",
                store="cache",
            ) from set_result.unwrap_err()

    async def _cache_delete(self, key: str) -> None:
        delete_result = await self._cache.delete(key)
        if delete_result.is_err():
            raise MemoryStoreError(
                f"Cache delete failed for key {key}",
                store="cache",
            ) from delete_result.unwrap_err()

    async def store(self, entry: MemoryEntry) -> None:
        await self._cache_set_text(
            self._key(entry.id), self._to_json(entry), ttl=self._ttl
        )
        index_raw = await self._cache_get_text(_INDEX_KEY)
        ids: list[str] = cast("list[str]", loads(index_raw)) if index_raw else []
        if entry.id not in ids:
            ids.append(entry.id)
            await self._cache_set_text(_INDEX_KEY, dumps_str(ids))

    async def retrieve(self, query: MemoryQuery) -> list[MemorySearchResult]:
        index_raw = await self._cache_get_text(_INDEX_KEY)
        if index_raw is None:
            return []

        ids = cast("list[str]", loads(index_raw))
        entries: list[MemoryEntry] = []
        for entry_id in ids:
            raw = await self._cache_get_text(self._key(entry_id))
            if raw is not None:
                entries.append(self._from_json(raw))

        import math

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
            scored.append((score, entry))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            MemorySearchResult(entry=entry, score=score, source="cache")
            for score, entry in scored[: query.top_k]
        ]

    async def get_recent(self, n: int) -> list[MemoryEntry]:
        index_raw = await self._cache_get_text(_INDEX_KEY)
        if index_raw is None:
            return []

        ids = cast("list[str]", loads(index_raw))
        entries: list[MemoryEntry] = []
        for entry_id in ids:
            raw = await self._cache_get_text(self._key(entry_id))
            if raw is not None:
                entries.append(self._from_json(raw))
        return sorted(entries, key=lambda entry: entry.timestamp, reverse=True)[:n]

    async def delete(self, entry_id: str) -> None:
        await self._cache_delete(self._key(entry_id))
        index_raw = await self._cache_get_text(_INDEX_KEY)
        if index_raw is None:
            return
        remaining_ids = [
            item for item in cast("list[str]", loads(index_raw)) if item != entry_id
        ]
        await self._cache_set_text(_INDEX_KEY, dumps_str(remaining_ids))

    async def clear(self) -> None:
        index_raw = await self._cache_get_text(_INDEX_KEY)
        if index_raw is not None:
            for entry_id in cast("list[str]", loads(index_raw)):
                await self._cache_delete(self._key(entry_id))
        await self._cache_delete(_INDEX_KEY)

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        health_result = await self._cache.health_check(timeout=timeout)
        status = HealthStatus.HEALTHY
        if not health_result.is_healthy():
            status = HealthStatus.DEGRADED
        return HealthCheckResult(
            component="memory.cache",
            status=status,
            message=health_result.message,
            error=health_result.error,
            details={"timeout": timeout},
        )


__all__ = ["CacheMemoryBackend"]
