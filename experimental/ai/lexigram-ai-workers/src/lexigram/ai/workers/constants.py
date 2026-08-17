"""Constants for AI Workers."""

from __future__ import annotations

import importlib.metadata

try:
    __version__: str = importlib.metadata.version("lexigram-ai-workers")
except ImportError:
    __version__ = "0.0.0"


DEFAULT_CHECK_INTERVAL: int = 60
"""Default interval in seconds between task checks."""

DEFAULT_MAX_RETRIES: int = 5
"""Default maximum retry attempts per failed job."""

DEFAULT_BASE_BACKOFF: int = 60
"""Default base delay in seconds for exponential backoff."""

MAX_BACKOFF_SECONDS: int = 3600
"""Maximum backoff delay (1 hour)."""

DEFAULT_TASK_TIMEOUT: float = 300.0
"""Default task timeout in seconds (5 minutes)."""

MAX_HISTORY_SIZE: int = 1000
"""Maximum maintenance result history entries to retain."""

# ---------------------------------------------------------------------------
# Environment Variable Prefixes
# ---------------------------------------------------------------------------

ENV_PREFIX: str = "LEX_AI_WORKERS__"
"""Environment variable prefix for AI workers configuration."""

ENV_NESTED_DELIMITER: str = "__"
"""Delimiter for nested env var keys."""


__all__ = [
    "DEFAULT_BASE_BACKOFF",
    "DEFAULT_CHECK_INTERVAL",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_TASK_TIMEOUT",
    "ENV_NESTED_DELIMITER",
    "ENV_PREFIX",
    "MAX_BACKOFF_SECONDS",
    "MAX_HISTORY_SIZE",
    "__version__",
]
