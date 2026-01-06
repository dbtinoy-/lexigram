"""AI feedback contracts and types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable
from uuid import uuid4

if TYPE_CHECKING:
    from lexigram.contracts.core.result import Result


class FeedbackType(StrEnum):
    """Type of feedback collected."""

    RATING = "rating"
    TEXT = "text"
    CORRECTION = "correction"
    LABEL = "label"


@dataclass(frozen=True)
class FeedbackItem:
    """A single feedback item.

    Attributes:
        feedback_type: Type of feedback (rating, text, correction, or label).
        value: The feedback value (e.g. rating score, text comment).
        context: Context about what was being evaluated (session_id, model, etc.).
        metadata: Additional metadata dictionary.
        id: Unique feedback identifier.
        created_at: Timestamp when feedback was created.
    """

    feedback_type: FeedbackType
    value: Any
    context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def type(self) -> FeedbackType:
        """Alias for feedback_type for backward compatibility.

        Returns:
            The feedback type.
        """
        return self.feedback_type

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation with ISO-formatted timestamp.
        """
        return {
            "id": self.id,
            "type": self.feedback_type.value,
            "value": self.value,
            "context": self.context,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"FeedbackItem(id={self.id}, "
            f"type={self.feedback_type.value}, value={self.value})"
        )


@dataclass(frozen=True)
class FeedbackSummary:
    """Aggregated statistics for collected feedback items.

    Attributes:
        total_count: Total number of feedback items in the window.
        average_rating: Mean rating across all RATING-type items,
            or None if no ratings were collected.
        count_by_type: Item count keyed by FeedbackType enum value
            (e.g. "rating", "text", "correction", "label").
    """

    total_count: int = 0
    average_rating: float | None = None
    count_by_type: dict[str, int] = field(default_factory=dict)


@runtime_checkable
class FeedbackStoreProtocol(Protocol):
    """Persist and query collected feedback items.

    All implementations must be async and treat save() as safe to
    call from request-handling hot-paths (synchronous returns acceptable
    for cache misses).
    """

    async def save(self, feedback: FeedbackItem) -> Result[str, Exception]:
        """Persist a single feedback item.

        Args:
            feedback: The feedback item to store.

        Returns:
            Ok(feedback.id) on success, Err(exception) on failure.
        """
        ...

    async def find_by_session(self, session_id: str) -> list[FeedbackItem]:
        """Retrieve all feedback items for a session.

        Args:
            session_id: Session identifier from feedback context.

        Returns:
            All collected items in that session, newest first.
        """
        ...

    async def find_by_type(
        self,
        feedback_type: FeedbackType,
        *,
        limit: int = 100,
    ) -> list[FeedbackItem]:
        """Retrieve feedback items of a given type.

        Args:
            feedback_type: The type to filter by.
            limit: Maximum number of results (default 100).

        Returns:
            Matching items ordered by creation time descending.
        """
        ...

    async def aggregate(self, *, window_hours: int = 24) -> FeedbackSummary:
        """Compute summary statistics for items in a time window.

        Args:
            window_hours: Look-back window in hours (default 24).

        Returns:
            Aggregated FeedbackSummary statistics.
        """
        ...


@runtime_checkable
class FeedbackProtocol(Protocol):
    """Protocol for submitting and querying AI feedback."""

    async def submit_feedback(
        self,
        trace_id: str,
        score: float,
        comment: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Submit feedback for an AI generation."""
        ...

    async def get_feedback_stats(
        self,
        model: str | None = None,
        provider: str | None = None,
    ) -> dict[str, Any]:
        """Query aggregate feedback statistics."""
        ...


__all__ = [
    "FeedbackItem",
    "FeedbackProtocol",
    "FeedbackStoreProtocol",
    "FeedbackSummary",
    "FeedbackType",
]
