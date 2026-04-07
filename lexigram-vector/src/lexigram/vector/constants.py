"""Package-level constants for lexigram-vector."""

from __future__ import annotations

import importlib.metadata

try:
    __version__: str = importlib.metadata.version("lexigram-vector")
except ImportError:
    __version__ = "0.0.0"


# Environment variable prefix
ENV_PREFIX: str = "LEX_VECTOR__"
ENV_NESTED_DELIMITER: str = "__"

# Default batch sizes
DEFAULT_UPSERT_BATCH_SIZE: int = 100
DEFAULT_DELETE_BATCH_SIZE: int = 1000
DEFAULT_QUERY_TOP_K: int = 10

# Health check
DEFAULT_HEALTH_CHECK_TIMEOUT: float = 5.0

# pgvector defaults
PGVECTOR_DEFAULT_LISTS: int = 100
PGVECTOR_DEFAULT_PROBES: int = 10
PGVECTOR_DEFAULT_EF_SEARCH: int = 64

# HNSW defaults
DEFAULT_HNSW_M: int = 16
DEFAULT_HNSW_EF_CONSTRUCTION: int = 200

# Connection
DEFAULT_CONNECT_TIMEOUT: float = 10.0
DEFAULT_REQUEST_TIMEOUT: float = 30.0
DEFAULT_MAX_RETRIES: int = 3
DEFAULT_RETRY_DELAY: float = 0.5

# Backend identifiers
BACKEND_MEMORY: str = "memory"
BACKEND_PGVECTOR: str = "pgvector"
BACKEND_PINECONE: str = "pinecone"
BACKEND_QDRANT: str = "qdrant"
BACKEND_CHROMA: str = "chroma"
BACKEND_WEAVIATE: str = "weaviate"


__all__ = [
    "BACKEND_CHROMA",
    "BACKEND_MEMORY",
    "BACKEND_PGVECTOR",
    "BACKEND_PINECONE",
    "BACKEND_QDRANT",
    "BACKEND_WEAVIATE",
    "DEFAULT_CONNECT_TIMEOUT",
    "DEFAULT_DELETE_BATCH_SIZE",
    "DEFAULT_HEALTH_CHECK_TIMEOUT",
    "DEFAULT_HNSW_EF_CONSTRUCTION",
    "DEFAULT_HNSW_M",
    "DEFAULT_QUERY_TOP_K",
    "DEFAULT_REQUEST_TIMEOUT",
    "DEFAULT_RETRY_DELAY",
    "DEFAULT_UPSERT_BATCH_SIZE",
    "ENV_NESTED_DELIMITER",
    "ENV_PREFIX",
    "PGVECTOR_DEFAULT_EF_SEARCH",
    "PGVECTOR_DEFAULT_LISTS",
    "PGVECTOR_DEFAULT_PROBES",
    "__version__",
]
