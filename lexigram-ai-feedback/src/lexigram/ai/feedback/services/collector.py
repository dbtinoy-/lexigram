"""Feedback collection system for continuous learning.

Collects user feedback on AI/ML predictions for model improvement.
"""

from __future__ import annotations

from typing import Any

from lexigram.ai.feedback.storage.protocols import FeedbackStoreProtocol
from lexigram.ai.feedback.types import FeedbackItem, FeedbackType


class FeedbackCollector:
    """Collects and stores user feedback.

    Provides methods to capture different types of feedback and
    integrate with ML retraining pipelines.

    Example:
        >>> collector = FeedbackCollector()
        >>> # Collect rating
        >>> await collector.collect_rating(
        ...     rating=5,
        ...     context={"model": "gpt-4", "input": "Hello"}
        ... )
        >>> # Collect correction
        >>> await collector.collect_correction(
        ...     original="incorrect output",
        ...     corrected="correct output",
        ...     context={"model_id": "123"}
        ... )
        >>> # Get all feedback
        >>> items = collector.get_feedback()
    """

    def __init__(self, storage: FeedbackStoreProtocol | None = None):
        """Initialize feedback collector.

        Args:
            storage: Optional storage backend (e.g., database, file)
                    If None, uses in-memory storage
        """
        self.storage = storage
        self._feedback: list[FeedbackItem] = []

    async def collect_rating(
        self,
        rating: float,
        context: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Collect a rating feedback.

        Args:
            rating: Numeric rating value
            context: Context about what was rated
            metadata: Additional metadata

        Returns:
            Feedback ID
        """
        item = FeedbackItem(
            feedback_type=FeedbackType.RATING,
            value=rating,
            context=context or {},
            metadata=metadata or {},
        )

        await self._store(item)
        return item.id

    async def collect_text(
        self,
        text: str,
        context: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Collect text feedback.

        Args:
            text: Feedback text
            context: Context about what feedback is for
            metadata: Additional metadata

        Returns:
            Feedback ID
        """
        item = FeedbackItem(
            feedback_type=FeedbackType.TEXT,
            value=text,
            context=context or {},
            metadata=metadata or {},
        )

        await self._store(item)
        return item.id

    async def collect_correction(
        self,
        original: str,
        corrected: str,
        context: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Collect a correction feedback.

        Args:
            original: Original (incorrect) output
            corrected: Corrected output
            context: Context
            metadata: Additional metadata

        Returns:
            Feedback ID
        """
        item = FeedbackItem(
            feedback_type=FeedbackType.CORRECTION,
            value={"original": original, "corrected": corrected},
            context=context or {},
            metadata=metadata or {},
        )

        await self._store(item)
        return item.id

    async def collect_label(
        self,
        label: Any,
        input_data: Any,
        context: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Collect ground truth label.

        Useful for supervised learning and model retraining.

        Args:
            label: Ground truth label
            input_data: Input that this label corresponds to
            context: Context
            metadata: Additional metadata

        Returns:
            Feedback ID
        """
        item = FeedbackItem(
            feedback_type=FeedbackType.LABEL,
            value={"label": label, "input": input_data},
            context=context or {},
            metadata=metadata or {},
        )

        await self._store(item)
        return item.id

    async def _store(self, item: FeedbackItem) -> None:
        """Store feedback item.

        Args:
            item: Feedback item to store
        """
        self._feedback.append(item)
        if self.storage:
            await self.storage.save(item)

    async def get_feedback(
        self,
        feedback_type: FeedbackType | None = None,
        limit: int | None = None,
    ) -> list[FeedbackItem]:
        """Get feedback items.

        Args:
            feedback_type: Optional filter by type
            limit: Maximum number of items to return

        Returns:
            List of feedback items from memory or the storage backend.
        """
        if self.storage:
            return await self._get_feedback_from_storage(feedback_type, limit)
        return self._filter_memory_feedback(feedback_type, limit)

    async def _get_feedback_from_storage(
        self,
        feedback_type: FeedbackType | None,
        limit: int | None,
    ) -> list[FeedbackItem]:
        if limit == 0:
            return []

        if self.storage is None:
            return []

        if feedback_type:
            per_type_limit = limit if limit is not None else 100
            return await self.storage.find_by_type(
                feedback_type,
                limit=per_type_limit,
            )

        per_type_limit = limit if limit is not None else 100
        results: list[FeedbackItem] = []
        for ft in FeedbackType:
            batch = await self.storage.find_by_type(ft, limit=per_type_limit)
            results.extend(batch)

        results.sort(key=lambda item: item.created_at, reverse=True)
        if limit:
            return results[:limit]
        return results

    def _filter_memory_feedback(
        self,
        feedback_type: FeedbackType | None,
        limit: int | None,
    ) -> list[FeedbackItem]:
        items = list(self._feedback)
        if feedback_type:
            items = [item for item in items if item.feedback_type == feedback_type]
        if limit is not None:
            items = items[:limit]
        return items

    async def get_feedback_dict(
        self,
        feedback_type: FeedbackType | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Get feedback as dictionaries.

        Args:
            feedback_type: Optional filter by type
            limit: Maximum number of items

        Returns:
            List of feedback dictionaries
        """
        items = await self.get_feedback(feedback_type, limit)
        return [item.to_dict() for item in items]

    def clear(self) -> None:
        """Clear all feedback from the in-memory buffer."""
        self._feedback.clear()

    def __len__(self) -> int:
        """Number of feedback items."""
        return len(self._feedback)

    def __repr__(self) -> str:
        """String representation."""
        return f"FeedbackCollector(items={len(self._feedback)})"
