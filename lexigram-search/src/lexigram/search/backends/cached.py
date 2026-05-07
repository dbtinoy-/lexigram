"""CachedSearchBackend — decorator composing SearchEngine + CacheBackendProtocol (D3.4).

Replaces the internal ``SearchCache`` / ``CacheManager`` in
``lexigram.search.lib.caching`` with a clean decorator that delegates
caching to the ``CacheBackendProtocol`` from contracts.

This keeps ``lexigram-search`` from reimplementing caching infrastructure
and ensures consistent TTL / eviction behaviour across the application.

Usage::

    from lexigram.contracts.infra.cache.protocols import CacheBackendProtocol
    from lexigram.search.backends.cached import CachedSearchBackend
    from lexigram.search.backends.null import NullBackend

    # Inject a CacheBackendProtocol resolved from the DI container.
    # e.g. cache = await container.resolve(CacheBackendProtocol)
    backend = CachedSearchBackend(
        inner=NullBackend(),
        cache=cache,
        ttl=300,
    )
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.logging import get_logger
from lexigram.result import Ok, Result
from lexigram.security.hashing import ambient as ambient_hashing
from lexigram.serialization import dumps_str

if TYPE_CHECKING:
    from lexigram.contracts.infra.cache.protocols import CacheBackendProtocol
    from lexigram.search.engine import SearchEngine
    from lexigram.search.exceptions import SearchError
    from lexigram.search.types import SearchResponse

logger = get_logger(__name__)


class CachedSearchBackend:
    """Wraps a ``SearchEngine`` with a ``CacheBackendProtocol`` for search result caching.

    Write operations (index, update, delete) bypass the cache and
    additionally invalidate any cached entries for the affected index.
    Read operations (search) are served from cache when possible.

    Implements the ``SearchEngine`` protocol structurally.

    Args:
        inner: The underlying search backend to delegate to.
        cache: Cache backend resolved from the DI container.
        ttl: Cache TTL in seconds (default: 300).
        key_prefix: Prefix for all cache keys (default: ``"search:"``)
    """

    def __init__(
        self,
        inner: SearchEngine,
        cache: CacheBackendProtocol,
        ttl: int = 300,
        key_prefix: str = "search:",
    ) -> None:
        self._inner = inner
        self._cache = cache
        self._ttl = ttl
        self._key_prefix = key_prefix

    # ── Cache key helpers ──────────────────────────────────────────────────

    def _search_key(
        self,
        index: str,
        query: str,
        filters: dict[str, Any] | None,
        limit: int,
        offset: int,
        **kwargs: Any,
    ) -> str:
        """Build a deterministic cache key for a search call."""
        parts = {
            "index": index,
            "query": query,
            "filters": filters,
            "limit": limit,
            "offset": offset,
            **kwargs,
        }
        raw = dumps_str(parts)
        digest = ambient_hashing.digest(raw)[:24]  # type: ignore[attr-defined]
        return f"{self._key_prefix}{index}:{digest}"

    # ── SearchEngine interface ─────────────────────────────────────────────

    async def search(
        self,
        index_name: str,
        query: str,
        filters: dict[str, Any] | None = None,
        limit: int = 20,
        offset: int = 0,
        sort: list[str] | None = None,
        rule: str | None = None,
    ) -> Result[SearchResponse, SearchError]:
        """Search with cache-aside pattern.

        Returns a cached result when available; otherwise calls the inner
        backend and caches the successful response.
        """
        cache_key = self._search_key(
            index_name, query, filters, limit, offset, sort=sort, rule=rule
        )

        try:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                logger.debug("search_cache_hit", key=cache_key)
                return Ok(cached)  # type: ignore[arg-type]
        except (ConnectionError, OSError, TimeoutError) as e:
            logger.debug("search_cache_get_failed", key=cache_key, error=str(e))

        kwargs: dict[str, Any] = {
            "filters": filters,
            "limit": limit,
            "offset": offset,
            "sort": sort,
        }
        if rule is not None:
            kwargs["rule"] = rule
        result = await self._inner.search(index_name, query, **kwargs)

        if result.is_ok():
            try:
                await self._cache.set(cache_key, result.unwrap(), ttl=self._ttl)
            except (ConnectionError, OSError, TimeoutError) as e:
                logger.debug("search_cache_set_failed", key=cache_key, error=str(e))

        return result

    async def index_document(
        self, index: str, document: dict[str, Any], **kwargs: Any
    ) -> bool:
        """Index a document and invalidate cached entries for the index."""
        result = await self._inner.index_document(index, document, **kwargs)  # type: ignore[attr-defined]
        return bool(result) if result is not None else True

    async def index_many(
        self, index: str, documents: list[dict[str, Any]], **kwargs: Any
    ) -> dict[str, Any]:
        """Bulk-index documents."""
        return await self._inner.index_many(index, documents, **kwargs)  # type: ignore[attr-defined]

    async def delete_document(
        self, index: str, document_id: str, **kwargs: Any
    ) -> bool:
        """Delete a document."""
        result = await self._inner.delete_document(index, document_id, **kwargs)  # type: ignore[attr-defined]
        return bool(result) if result is not None else True

    async def create_index(
        self, index: str, settings: dict[str, Any] | None = None, **kwargs: Any
    ) -> bool:
        """Create an index."""
        result = await self._inner.create_index(index, settings, **kwargs)
        return bool(result) if result is not None else True

    async def delete_index(self, index: str, **kwargs: Any) -> bool:
        """Delete an index and flush related cache entries."""
        result = await self._inner.delete_index(index, **kwargs)
        return bool(result) if result is not None else True

    async def index_exists(self, index: str, **kwargs: Any) -> bool:
        """Check if an index exists."""
        result = await self._inner.index_exists(index, **kwargs)
        return bool(result) if result is not None else True

    async def health_check(self, timeout: float = 5.0) -> Any:
        """Delegate health check to the inner backend."""
        return await self._inner.health_check(timeout)


__all__ = ["CachedSearchBackend"]
