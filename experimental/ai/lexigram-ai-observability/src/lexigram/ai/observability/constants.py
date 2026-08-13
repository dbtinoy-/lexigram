"""Constants for AI Observability."""

from __future__ import annotations

import importlib.metadata

try:
    __version__: str = importlib.metadata.version("lexigram-ai-observability")
except ImportError:
    __version__ = "0.0.0"


# Environment variable prefix
ENV_PREFIX: str = "LEX_AI_OBSERVABILITY__"
ENV_NESTED_DELIMITER: str = "__"

# Health check defaults
DEFAULT_CHECK_INTERVAL_SECONDS: int = 30
"""Default interval between health checks in seconds."""

DEFAULT_CHECK_TIMEOUT_SECONDS: float = 5.0
"""Default timeout for individual health checks."""

# Metric name prefixes
METRIC_PREFIX_LLM: str = "lexigram.ai.llm"
"""Metric name prefix for LLM operations."""

METRIC_PREFIX_VECTOR: str = "lexigram.ai.vector"
"""Metric name prefix for vector operations."""

METRIC_PREFIX_EMBEDDING: str = "lexigram.ai.embedding"
"""Metric name prefix for embedding operations."""

# Tracing span names
SPAN_LLM_CALL: str = "llm.call"
SPAN_VECTOR_QUERY: str = "vector.query"
SPAN_EMBEDDING_GENERATE: str = "embedding.generate"
SPAN_RAG_PIPELINE: str = "rag.pipeline"


__all__ = [
    "DEFAULT_CHECK_INTERVAL_SECONDS",
    "DEFAULT_CHECK_TIMEOUT_SECONDS",
    "ENV_NESTED_DELIMITER",
    "ENV_PREFIX",
    "METRIC_PREFIX_EMBEDDING",
    "METRIC_PREFIX_LLM",
    "METRIC_PREFIX_VECTOR",
    "SPAN_EMBEDDING_GENERATE",
    "SPAN_LLM_CALL",
    "SPAN_RAG_PIPELINE",
    "SPAN_VECTOR_QUERY",
    "__version__",
]
