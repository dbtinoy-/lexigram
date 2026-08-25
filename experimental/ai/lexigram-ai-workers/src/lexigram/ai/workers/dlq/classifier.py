"""Error classification for DLQ failure routing."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.ai.workers.types import FailureCategory

if TYPE_CHECKING:
    from lexigram.contracts import JobProtocol


class ErrorClassifier:
    """Classify errors into failure categories."""

    @staticmethod
    def classify(error: str, _job: JobProtocol) -> FailureCategory:
        """
        Classify error into a failure category.

        Args:
            error: Error message
            job: Original job

        Returns:
            Failure category
        """
        error_lower = error.lower()

        # Permanent failures
        if any(
            term in error_lower
            for term in [
                "not found",
                "does not exist",
                "invalid",
                "malformed",
                "syntax error",
            ]
        ):
            return FailureCategory.PERMANENT

        # Throttling
        if any(
            term in error_lower
            for term in [
                "rate limit",
                "too many requests",
                "throttled",
                "quota exceeded",
            ]
        ):
            return FailureCategory.THROTTLED

        # Invalid input
        if any(
            term in error_lower
            for term in [
                "validation error",
                "invalid input",
                "bad request",
            ]
        ):
            return FailureCategory.INVALID_INPUT

        # Transient failures
        if any(
            term in error_lower
            for term in [
                "timeout",
                "connection",
                "network",
                "temporary",
                "unavailable",
                "503",
                "502",
            ]
        ):
            return FailureCategory.TRANSIENT

        return FailureCategory.UNKNOWN


__all__ = ["ErrorClassifier"]
