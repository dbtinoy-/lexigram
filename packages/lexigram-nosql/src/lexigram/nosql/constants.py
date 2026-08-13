"""Default constants for NoSQL operations."""

from __future__ import annotations

import importlib.metadata

try:
    __version__: str = importlib.metadata.version("lexigram-nosql")
except ImportError:
    __version__ = "0.0.0"


# ---------------------------------------------------------------------------
# Environment Variable Prefixes
# ---------------------------------------------------------------------------

ENV_PREFIX: str = "LEX_NOSQL__"
"""Environment variable prefix for NoSQL configuration."""

ENV_NESTED_DELIMITER: str = "__"
"""Delimiter for nested env var keys."""


# Connection pool defaults
DEFAULT_MAX_POOL_SIZE: int = 100
DEFAULT_MIN_POOL_SIZE: int = 10

# Timeout defaults (milliseconds)
DEFAULT_SERVER_SELECTION_TIMEOUT_MS: int = 5000
DEFAULT_CONNECT_TIMEOUT_MS: int = 10000
DEFAULT_SOCKET_TIMEOUT_MS: int = 30000

# Health check
DEFAULT_HEALTH_CHECK_TIMEOUT: float = 5.0

# Query defaults
DEFAULT_QUERY_LIMIT: int = 100
DEFAULT_BATCH_SIZE: int = 1000


__all__ = [
    "DEFAULT_BATCH_SIZE",
    "DEFAULT_CONNECT_TIMEOUT_MS",
    "DEFAULT_HEALTH_CHECK_TIMEOUT",
    "DEFAULT_MAX_POOL_SIZE",
    "DEFAULT_MIN_POOL_SIZE",
    "DEFAULT_QUERY_LIMIT",
    "DEFAULT_SERVER_SELECTION_TIMEOUT_MS",
    "DEFAULT_SOCKET_TIMEOUT_MS",
    "ENV_NESTED_DELIMITER",
    "ENV_PREFIX",
    "__version__",
]
