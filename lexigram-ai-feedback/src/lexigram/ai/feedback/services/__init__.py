"""Feedback services."""

from __future__ import annotations

from lexigram.ai.feedback.services.feedback_service import FeedbackService
from lexigram.ai.feedback.services.result_pattern_service import (
    FeedbackSystemWithResultPattern,
)

__all__ = ["FeedbackService", "FeedbackSystemWithResultPattern"]
