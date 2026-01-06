"""Exception hierarchy for AI Feedback."""

from __future__ import annotations

from lexigram.contracts.ai.exceptions import AIError


class FeedbackError(AIError):
    """Base exception for all feedback-related errors."""

    _code: str = "LEX_ERR_FEED_001"


class FeedbackProcessingError(FeedbackError):
    """Raised when a feedback processor fails."""

    _code: str = "LEX_ERR_FEED_002"


class FeedbackValidationError(FeedbackError):
    """Raised when feedback data fails validation."""

    _code: str = "LEX_ERR_FEED_003"


__all__ = [
    "FeedbackError",
    "FeedbackProcessingError",
    "FeedbackValidationError",
]
