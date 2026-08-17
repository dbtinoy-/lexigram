"""Feedback collection system for continuous learning.

Collects user feedback on AI/ML predictions for model improvement.
"""

from __future__ import annotations

from typing import Any

from lexigram.ai.feedback.constants import MAX_CONTEXT_SIZE, MAX_FEEDBACK_TEXT_LENGTH
from lexigram.ai.feedback.exceptions import FeedbackTooLargeError
from lexigram.ai.feedback.storage.protocols import FeedbackStoreProtocol
from lexigram.ai.feedback.types import FeedbackItem, FeedbackType
from lexigram.serialization import dumps_str


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
        *,
        owner_id: str,
        context: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Collect a rating feedback.

        Args:
            rating: Numeric rating value.
            owner_id: Owner scope; the item is recorded under this owner.
            context: Context about what was rated.
            metadata: Additional metadata.

        Returns:
            Feedback ID.
        """
        item = FeedbackItem(
            feedback_type=FeedbackType.RATING,
            value=rating,
            owner_id=owner_id,
            context=context or {},
            metadata=metadata or {},
        )

        await self._store(item)
        return item.id

    async def collect_text(
        self,
        text: str,
        *,
        owner_id: str,
        context: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Collect text feedback.

        Args:
            text: Feedback text.
            owner_id: Owner scope; the item is recorded under this owner.
            context: Context about what feedback is for.
            metadata: Additional metadata.

        Returns:
            Feedback ID.
        """
        item = FeedbackItem(
            feedback_type=FeedbackType.TEXT,
            value=text,
            owner_id=owner_id,
            context=context or {},
            metadata=metadata or {},
        )

        await self._store(item)
        return item.id

    async def collect_correction(
        self,
        original: str,
        corrected: str,
        *,
        owner_id: str,
        context: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Collect a correction feedback.

        Args:
            original: Original (incorrect) output.
            corrected: Corrected output.
            owner_id: Owner scope; the item is recorded under this owner.
            context: Context.
            metadata: Additional metadata.

        Returns:
            Feedback ID.
        """
        item = FeedbackItem(
            feedback_type=FeedbackType.CORRECTION,
            value={"original": original, "corrected": corrected},
            owner_id=owner_id,
            context=context or {},
            metadata=metadata or {},
        )

        await self._store(item)
        return item.id

    async def collect_label(
        self,
        label: Any,
        input_data: Any,
        *,
        owner_id: str,
        context: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Collect ground truth label.

        Useful for supervised learning and model retraining.

        Args:
            label: Ground truth label.
            input_data: Input that this label corresponds to.
            owner_id: Owner scope; the item is recorded under this owner.
            context: Context.
            metadata: Additional metadata.

        Returns:
            Feedback ID.
        """
        item = FeedbackItem(
            feedback_type=FeedbackType.LABEL,
            value={"label": label, "input": input_data},
            owner_id=owner_id,
            context=context or {},
            metadata=metadata or {},
        )

        await self._store(item)
        return item.id

    async def _store(self, item: FeedbackItem) -> None:
        """Store feedback item, enforcing the declared size limits.

        Rejects payloads exceeding MAX_FEEDBACK_TEXT_LENGTH (TEXT values)
        or MAX_CONTEXT_SIZE (serialized context/metadata) with
        FeedbackTooLargeError before any mutation.

        Args:
            item: Feedback item to store

        Raises:
            FeedbackTooLargeError: If the item exceeds the size limits.
        """
        if (
            item.feedback_type == FeedbackType.TEXT
            and isinstance(item.value, str)
            and len(item.value) > MAX_FEEDBACK_TEXT_LENGTH
        ):
            raise FeedbackTooLargeError(
                f"feedback text exceeds the {MAX_FEEDBACK_TEXT_LENGTH}-character limit"
            )
        if len(dumps_str(item.context, default=str)) > MAX_CONTEXT_SIZE:
            raise FeedbackTooLargeError(
                f"serialized context exceeds the {MAX_CONTEXT_SIZE}-character limit"
            )
        if len(dumps_str(item.metadata, default=str)) > MAX_CONTEXT_SIZE:
            raise FeedbackTooLargeError(
                f"serialized metadata exceeds the {MAX_CONTEXT_SIZE}-character limit"
            )
        self._feedback.append(item)
        if self.storage:
            await self.storage.save(item)

    async def get_feedback(
        self,
        *,
        owner_id: str,
        feedback_type: FeedbackType | None = None,
        limit: int | None = None,
    ) -> list[FeedbackItem]:
        """Get feedback items for an owner.

        Args:
            owner_id: Owner scope; only this owner's items are returned.
            feedback_type: Optional filter by type.
            limit: Maximum number of items to return.

        Returns:
            List of feedback items from memory or the storage backend.
        """
        if self.storage:
            return await self._get_feedback_from_storage(
                owner_id=owner_id,
                feedback_type=feedback_type,
                limit=limit,
            )
        return self._filter_memory_feedback(
            owner_id=owner_id, feedback_type=feedback_type, limit=limit
        )

    async def _get_feedback_from_storage(
        self,
        *,
        owner_id: str,
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
                owner_id=owner_id,
                limit=per_type_limit,
            )

        per_type_limit = limit if limit is not None else 100
        results: list[FeedbackItem] = []
        for ft in FeedbackType:
            batch = await self.storage.find_by_type(
                ft, owner_id=owner_id, limit=per_type_limit
            )
            results.extend(batch)

        results.sort(key=lambda item: item.created_at, reverse=True)
        if limit:
            return results[:limit]
        return results

    def _filter_memory_feedback(
        self,
        *,
        owner_id: str,
        feedback_type: FeedbackType | None,
        limit: int | None,
    ) -> list[FeedbackItem]:
        items = [item for item in self._feedback if item.owner_id == owner_id]
        if feedback_type:
            items = [item for item in items if item.feedback_type == feedback_type]
        if limit is not None:
            items = items[:limit]
        return items

    async def get_feedback_dict(
        self,
        *,
        owner_id: str,
        feedback_type: FeedbackType | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Get feedback as dictionaries for an owner.

        Args:
            owner_id: Owner scope; only this owner's items are returned.
            feedback_type: Optional filter by type.
            limit: Maximum number of items.

        Returns:
            List of feedback dictionaries.
        """
        items = await self.get_feedback(
            owner_id=owner_id, feedback_type=feedback_type, limit=limit
        )
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
