"""Feature flag exception classes for the Lexigram Framework.

Defines all expected failures in the feature flag evaluation lifecycle,
from missing flags to provider-level evaluation errors.
"""

from __future__ import annotations

from typing import Any

from lexigram.contracts.exceptions.base import LexigramError


class FeatureFlagError(LexigramError):
    """Base error for the feature flag subsystem."""

    _code = "LEX_ERR_FEAT_001"

    def __init__(self, message: str = "Feature flag error", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)


__all__ = [
    "FeatureFlagError",
]
