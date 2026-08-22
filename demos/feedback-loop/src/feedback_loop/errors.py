"""Typed CLI-boundary errors for the feedback-loop demo."""

from __future__ import annotations


class UnknownQuestionError(ValueError):
    """Raised when an unknown question key is asked."""


class UnknownTraceError(ValueError):
    """Raised when rating an unissued trace id."""


class InvalidRatingError(ValueError):
    """Raised when a rating is outside the closed interval [1, 5]."""


class NoLowRatedError(ValueError):
    """Raised when a regression run has no low-rated feedback to use."""
