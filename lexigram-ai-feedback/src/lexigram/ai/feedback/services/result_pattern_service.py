"""Feedback system service using Result pattern."""

from __future__ import annotations

from lexigram.contracts.ai.exceptions import AIError
from lexigram.logging import (
    get_logger,
)
from lexigram.result import Err, Ok, Result

logger = get_logger(__name__)


class FeedbackSystemWithResultPattern:
    """Feedback system using Result pattern."""

    async def record_feedback(
        self,
        interaction_id: str,
        rating: float,
        comment: str = "",
    ) -> Result[str, AIError]:
        """Record user feedback."""
        del comment
        if not interaction_id:
            return Err(AIError("Interaction ID cannot be empty"))
        if not (0 <= rating <= 5):
            return Err(AIError("Rating must be between 0 and 5"))
        feedback_id = f"feedback:{interaction_id}"
        logger.info("feedback_recorded", interaction_id=interaction_id, rating=rating)
        return Ok(feedback_id)

    async def get_feedback(self, interaction_id: str) -> Result[list[dict], AIError]:
        """Get feedback for an interaction."""
        if not interaction_id:
            return Err(AIError("Interaction ID cannot be empty"))
        logger.info("feedback_retrieved", interaction_id=interaction_id)
        return Ok([])


__all__ = ["FeedbackSystemWithResultPattern"]
