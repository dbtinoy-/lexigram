"""lexigram-queue constants."""

from __future__ import annotations

import importlib.metadata

try:
    __version__ = importlib.metadata.version("lexigram-queue")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0"


# ---------------------------------------------------------------------------
# Environment Variable Prefixes
# ---------------------------------------------------------------------------

ENV_PREFIX: str = "LEX_QUEUE__"
ENV_NESTED_DELIMITER: str = "__"


DEFAULT_CONSUMER_CONCURRENCY: int = 4
DEFAULT_CONSUMER_PREFETCH: int = 10
DEFAULT_MAX_RETRIES: int = 3
DEFAULT_VISIBILITY_TIMEOUT: int = 30

__all__ = [
    "DEFAULT_CONSUMER_CONCURRENCY",
    "DEFAULT_CONSUMER_PREFETCH",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_VISIBILITY_TIMEOUT",
    "ENV_NESTED_DELIMITER",
    "ENV_PREFIX",
]
