"""Write-through cache feedback store.

Wraps a durable :class:`~lexigram.ai.feedback.storage.protocols.FeedbackStoreProtocol`
with a :class:`~lexigram.contracts.cache.CacheBackendProtocol` for fast reads.
All writes go to both the backing store and the cache in a write-through
fashion; cache entries are invalidated on any mutation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.logging import (
    get_logger,
)

if TYPE_CHECKING:
    from lexigram.ai.feedback.storage.protocols import (
        FeedbackStoreProtocol,
        FeedbackSummary,
    )
    from lexigram.ai.feedback.types import FeedbackItem, FeedbackType
    from lexigram.contracts.infra.cache import CacheBackendProtocol
    from lexigram.result import Result

logger = get_logger(__name__)

_SESSION_TTL = 300  # 5 minutes
_TYPE_TTL = 60  # 1 minute


def _session_key(session_id: str) -> str:
    return f"feedback:session:{session_id}"


def _type_key(feedback_type: FeedbackType) -> str:
    return f"feedback:type:{feedback_type.value}"


class CachedFeedbackStore:
    """Write-through cache: cold reads from *store*, hot reads from *cache*.

    Session-scoped and type-scoped result lists are cached with short TTLs.
    Any :meth:`save` call invalidates the relevant cache entries so subsequent
    reads always reflect the latest data.

    Args:
        store: Durable backing store (e.g. :class:`~lexigram.ai.feedback.storage.database.DatabaseFeedbackStore`).
        cache: Cache backend used for hot reads.
    """

    def __init__(
        self,
        store: FeedbackStoreProtocol,
        cache: CacheBackendProtocol,
    ) -> None:
        self._store = store
        self._cache = cache

    async def save(self, feedback: FeedbackItem) -> Result[str, Exception]:
        """Persist *feedback* and invalidate related cache entries.

        Args:
            feedback: Item to persist.

        Returns:
            Result from the backing store.
        """
        result = await self._store.save(feedback)
        if result.is_ok():
            session_id: str | None = feedback.context.get("session_id")
            if session_id:
                await self._cache.delete(_session_key(session_id))
            await self._cache.delete(_type_key(feedback.feedback_type))
            logger.debug(
                "feedback_cache_invalidated",
                feedback_id=feedback.id,
                session_id=session_id,
            )
        return result

    async def find_by_session(self, session_id: str) -> list[FeedbackItem]:
        """Return items for *session_id*, using cache when available.

        Args:
            session_id: Session identifier.

        Returns:
            Feedback items for the session, newest first.
        """
        cached = await self._cache.get(_session_key(session_id))
        if cached is not None:
            logger.debug("feedback_cache_hit", key=_session_key(session_id))
            return cached  # type: ignore[return-value]

        items = await self._store.find_by_session(session_id)
        await self._cache.set(_session_key(session_id), items, ttl=_SESSION_TTL)
        return items

    async def find_by_type(
        self,
        feedback_type: FeedbackType,
        *,
        limit: int = 100,
    ) -> list[FeedbackItem]:
        """Return items of *feedback_type*, using cache when available.

        Args:
            feedback_type: Type to filter by.
            limit: Maximum result count.

        Returns:
            Matching feedback items, newest first.
        """
        cached = await self._cache.get(_type_key(feedback_type))
        if cached is not None:
            logger.debug("feedback_cache_hit", key=_type_key(feedback_type))
            items: list[FeedbackItem] = cached  # type: ignore[assignment]
            return items[:limit]

        items = await self._store.find_by_type(feedback_type, limit=limit)
        await self._cache.set(_type_key(feedback_type), items, ttl=_TYPE_TTL)
        return items

    async def aggregate(self, *, window_hours: int = 24) -> FeedbackSummary:
        """Delegate aggregation to the backing store — not cached.

        Args:
            window_hours: Look-back window in hours.

        Returns:
            :class:`~lexigram.ai.feedback.storage.protocols.FeedbackSummary`.
        """
        return await self._store.aggregate(window_hours=window_hours)


__all__ = ["CachedFeedbackStore"]
