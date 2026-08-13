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


class FeedbackAuthorizationError(FeedbackError):
    """Raised when the endpoint's authorization callback denies a submission."""

    _code: str = "LEX_ERR_FEED_004"


class FeedbackTooLargeError(FeedbackValidationError):
    """Raised when a payload exceeds MAX_FEEDBACK_TEXT_LENGTH or MAX_CONTEXT_SIZE."""

    _code: str = "LEX_ERR_FEED_005"


__all__ = [
    "FeedbackAuthorizationError",
    "FeedbackError",
    "FeedbackProcessingError",
    "FeedbackTooLargeError",
    "FeedbackValidationError",
]
