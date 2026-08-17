"""Root hook payload surface for lexigram-ai-feedback."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "FeedbackProcessedHook",
    "FeedbackStoredHook",
    "FeedbackSubmittedHook",
]


@dataclass(frozen=True, kw_only=True)
class FeedbackSubmittedHook:
    """Payload fired when feedback is submitted to the feedback pipeline."""

    feedback_type: str


@dataclass(frozen=True, kw_only=True)
class FeedbackProcessedHook:
    """Payload fired when feedback processing finishes."""

    feedback_type: str


@dataclass(frozen=True, kw_only=True)
class FeedbackStoredHook:
    """Payload fired when feedback is persisted by a feedback store."""

    feedback_type: str
