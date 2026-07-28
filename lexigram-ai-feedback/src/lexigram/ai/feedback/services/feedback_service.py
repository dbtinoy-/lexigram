"""High-level feedback submission and aggregation service."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.ai.feedback import (
    FeedbackItem,
    FeedbackStoreProtocol,
    FeedbackType,
)
from lexigram.logging import (
    get_logger,
)

__all__ = ["FeedbackService"]

logger = get_logger(__name__)


class FeedbackService:
    """High-level feedback submission and querying service.

    Implements :class:`~lexigram.contracts.ai.feedback.FeedbackProtocol`.
    Wraps a :class:`~lexigram.contracts.ai.feedback.FeedbackStoreProtocol`
    with trace-id correlation and aggregation logic.

    Args:
        store: Optional storage backend; when ``None`` the service operates
               in a degraded no-op mode and logs warnings instead of persisting.
    """

    def __init__(self, store: FeedbackStoreProtocol | None = None) -> None:
        self._store = store

    async def submit_feedback(
        self,
        trace_id: str,
        score: float,
        comment: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Submit feedback for a traced AI generation.

        Args:
            trace_id: Identifier of the AI generation trace.
            score: Numeric feedback score (e.g. 0.0–1.0 or 1–5).
            comment: Optional free-text comment stored in metadata.
            metadata: Optional additional key-value metadata.
        """
        if self._store is None:
            logger.debug("feedback_store_unavailable", trace_id=trace_id)
            return

        meta: dict[str, Any] = dict(metadata or {})
        if comment is not None:
            meta["comment"] = comment

        item = FeedbackItem(
            feedback_type=FeedbackType.RATING,
            value=score,
            context={"trace_id": trace_id},
            metadata=meta,
        )

        result = await self._store.save(item)
        if result.is_ok():
            logger.info("feedback_submitted", trace_id=trace_id, score=score)
        else:
            logger.error(
                "feedback_submit_failed",
                trace_id=trace_id,
                error=str(result.unwrap_err()),
            )

    async def get_feedback_stats(
        self,
        model: str | None = None,
        provider: str | None = None,
    ) -> dict[str, Any]:
        """Get aggregate feedback statistics.

        Args:
            model: Optional model name for context (currently informational).
            provider: Optional provider name for context (currently informational).

        Returns:
            Dictionary with ``total_count``, ``average_rating``, and
            ``by_type`` breakdown, plus optional ``model``/``provider`` keys
            when supplied.
        """
        if self._store is None:
            logger.debug("feedback_store_unavailable")
            return {"total_count": 0, "average_rating": None, "by_type": {}}

        summary = await self._store.aggregate(window_hours=24)
        stats: dict[str, Any] = {
            "total_count": summary.total_count,
            "average_rating": summary.average_rating,
            "by_type": summary.count_by_type,
        }
        if model is not None:
            stats["model"] = model
        if provider is not None:
            stats["provider"] = provider
        return stats
