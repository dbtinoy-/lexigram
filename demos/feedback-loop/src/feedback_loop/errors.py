"""Typed domain errors for the feedback-loop demo.

Subclass contracts domain errors so the web Result-bridge maps them to
semantic HTTP statuses automatically.
"""

from __future__ import annotations

from lexigram.contracts.exceptions.domain import (
    ConflictError,
    NotFoundError,
    ValidationError,
)


class UnknownQuestionError(NotFoundError):
    """Raised when an unknown question key is asked."""


class UnknownTraceError(NotFoundError):
    """Raised when rating an unissued trace id."""


class InvalidRatingError(ValidationError):
    """Raised when a rating is outside the closed interval [1, 5]."""


class NoLowRatedError(ConflictError):
    """Raised when a regression run has no low-rated feedback to use."""
