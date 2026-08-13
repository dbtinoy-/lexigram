"""Constants for AI Feedback."""

from __future__ import annotations

import importlib.metadata

try:
    __version__: str = importlib.metadata.version("lexigram-ai-feedback")
except ImportError:
    __version__ = "0.0.0"


# Environment variable prefix
ENV_PREFIX: str = "LEX_AI_FEEDBACK__"
ENV_NESTED_DELIMITER: str = "__"

MAX_FEEDBACK_TEXT_LENGTH: int = 10_000
"""Maximum length for text feedback in characters."""

DEFAULT_RATING_MIN: float = 1.0
"""Minimum value for rating feedback."""

DEFAULT_RATING_MAX: float = 5.0
"""Maximum value for rating feedback."""

MAX_CONTEXT_SIZE: int = 50_000
"""Maximum size of context dict when serialized, in characters."""


__all__ = [
    "DEFAULT_RATING_MAX",
    "DEFAULT_RATING_MIN",
    "ENV_NESTED_DELIMITER",
    "ENV_PREFIX",
    "MAX_CONTEXT_SIZE",
    "MAX_FEEDBACK_TEXT_LENGTH",
    "__version__",
]
