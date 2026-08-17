"""RAG constants — pipeline defaults, chunk limits, and metric names."""

from __future__ import annotations

import importlib.metadata

try:
    __version__: str = importlib.metadata.version("lexigram-ai-rag")
except ImportError:
    __version__ = "0.0.0"


# -- Environment Variable Prefixes -------------------------------------------
ENV_PREFIX: str = "LEX_AI_RAG__"
"""Environment variable prefix for RAG configuration."""

ENV_NESTED_DELIMITER: str = "__"
"""Delimiter for nested env var keys."""


# ---------------------------------------------------------------------------
# Chunking defaults
# ---------------------------------------------------------------------------

DEFAULT_CHUNK_SIZE: int = 512
DEFAULT_CHUNK_OVERLAP: int = 50

# ---------------------------------------------------------------------------
# Retrieval defaults
# ---------------------------------------------------------------------------

DEFAULT_TOP_K: int = 5
DEFAULT_SIMILARITY_THRESHOLD: float = 0.7
DEFAULT_RERANKING_TOP_N: int = 3

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

DEFAULT_QUERY_CACHE_TTL_S: int = 3600
DEFAULT_EMBEDDING_CACHE_SIZE: int = 10_000

# ---------------------------------------------------------------------------
# MetricProtocol names
# ---------------------------------------------------------------------------

METRIC_RAG_PIPELINE_DURATION_MS: str = "ai.rag.pipeline.duration_ms"
METRIC_RAG_RETRIEVED_CHUNKS: str = "ai.rag.retrieved.chunks"
METRIC_RAG_CACHE_HITS: str = "ai.rag.cache.hits"

__all__ = [
    "DEFAULT_CHUNK_OVERLAP",
    "DEFAULT_CHUNK_SIZE",
    "DEFAULT_EMBEDDING_CACHE_SIZE",
    "DEFAULT_QUERY_CACHE_TTL_S",
    "DEFAULT_RERANKING_TOP_N",
    "DEFAULT_SIMILARITY_THRESHOLD",
    "DEFAULT_TOP_K",
    "ENV_NESTED_DELIMITER",
    "ENV_PREFIX",
    "METRIC_RAG_CACHE_HITS",
    "METRIC_RAG_PIPELINE_DURATION_MS",
    "METRIC_RAG_RETRIEVED_CHUNKS",
    "__version__",
]
