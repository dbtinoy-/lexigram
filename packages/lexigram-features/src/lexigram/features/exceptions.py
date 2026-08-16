"""Exceptions for the feature-flag subsystem.

All exceptions derive from :class:`FeatureFlagError` (defined in
``lexigram.contracts``) so they can be caught uniformly at the package level.
"""

from __future__ import annotations

from typing import Any

from lexigram.contracts.exceptions.feature_flags import FeatureFlagError


class FlagNotFoundError(FeatureFlagError):
    """Raised when a requested feature flag does not exist in any provider.

    Attributes:
        flag_key: The key of the missing flag.
    """

    _code = "LEX_ERR_FEAT_002"

    def __init__(self, flag_key: str, **kwargs: Any) -> None:
        super().__init__(f"Feature flag not found: {flag_key!r}", **kwargs)
        self.flag_key = flag_key


class FlagEvaluationError(FeatureFlagError):
    """Raised when a flag provider fails during evaluation.

    Attributes:
        flag_key: The key of the flag that failed to evaluate.
    """

    _code = "LEX_ERR_FEAT_003"

    def __init__(
        self,
        flag_key: str,
        message: str = "Flag evaluation failed",
        **kwargs: Any,
    ) -> None:
        super().__init__(f"{message}: {flag_key!r}", **kwargs)
        self.flag_key = flag_key


class FeatureFlagDisabledError(FeatureFlagError):
    """Raised when a feature-guarded path is called with the flag disabled."""

    _code = "LEX_ERR_FEAT_004"

    def __init__(self, flag_name: str) -> None:
        super().__init__(f"Feature flag is disabled: {flag_name!r}")
        self.flag_name = flag_name


__all__ = [
    "FeatureFlagDisabledError",
    "FeatureFlagError",
    "FlagEvaluationError",
    "FlagNotFoundError",
]
