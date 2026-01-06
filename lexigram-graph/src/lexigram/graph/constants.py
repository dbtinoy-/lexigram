"""Graph store constants."""

from __future__ import annotations

import importlib.metadata

try:
    __version__: str = importlib.metadata.version("lexigram-graph")
except ImportError:
    __version__ = "0.0.0"


# Environment variable prefix
ENV_PREFIX: str = "LEX_GRAPH__"

ENV_NESTED_DELIMITER: str = "__"
"""Nested delimiter for environment variable configuration."""


# Backend identifiers
BACKEND_MEMORY = "memory"
BACKEND_NEO4J = "neo4j"

# Defaults
DEFAULT_MEMORY_MAX_NODES = 1_000_000
DEFAULT_MEMORY_MAX_EDGES = 5_000_000
DEFAULT_NEO4J_DATABASE = "neo4j"
DEFAULT_NEO4J_MAX_POOL_SIZE = 100
DEFAULT_NEO4J_FETCH_SIZE = 100
DEFAULT_CONNECT_TIMEOUT = 30.0
DEFAULT_TRAVERSAL_MAX_DEPTH = 10
DEFAULT_QUERY_LIMIT = 100
DEFAULT_BULK_BATCH_SIZE = 1000
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0


__all__ = [
    "BACKEND_MEMORY",
    "BACKEND_NEO4J",
    "DEFAULT_BULK_BATCH_SIZE",
    "DEFAULT_CONNECT_TIMEOUT",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_MEMORY_MAX_EDGES",
    "DEFAULT_MEMORY_MAX_NODES",
    "DEFAULT_NEO4J_DATABASE",
    "DEFAULT_NEO4J_FETCH_SIZE",
    "DEFAULT_NEO4J_MAX_POOL_SIZE",
    "DEFAULT_QUERY_LIMIT",
    "DEFAULT_RETRY_DELAY",
    "DEFAULT_TRAVERSAL_MAX_DEPTH",
    "ENV_NESTED_DELIMITER",
    "ENV_PREFIX",
    "__version__",
]
