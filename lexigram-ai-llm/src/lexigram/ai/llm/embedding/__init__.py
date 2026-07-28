"""Embedding provider adapters and registry.

Provides a unified interface for multiple embedding providers including OpenAI,
Cohere, Voyage, Jina, and local models via sentence-transformers.
"""

from __future__ import annotations

from lexigram.ai.llm.embedding.base import (
    AbstractEmbeddingAdapter,
    EmbeddingModelInfo,
)
from lexigram.ai.llm.embedding.cohere import CohereEmbeddingAdapter
from lexigram.ai.llm.embedding.config import (
    CohereEmbeddingConfig,
    EmbeddingConfig,
    JinaEmbeddingConfig,
    LocalEmbeddingConfig,
    OpenAIEmbeddingConfig,
    VoyageEmbeddingConfig,
)
from lexigram.ai.llm.embedding.jina import JinaEmbeddingAdapter
from lexigram.ai.llm.embedding.local import LocalEmbeddingAdapter
from lexigram.ai.llm.embedding.openai import OpenAIEmbeddingAdapter
from lexigram.ai.llm.embedding.registry import EmbeddingProviderRegistry
from lexigram.ai.llm.embedding.voyage import VoyageEmbeddingAdapter

__all__ = [
    "AbstractEmbeddingAdapter",
    "CohereEmbeddingAdapter",
    "CohereEmbeddingConfig",
    "EmbeddingConfig",
    "EmbeddingModelInfo",
    "EmbeddingProviderRegistry",
    "JinaEmbeddingAdapter",
    "JinaEmbeddingConfig",
    "LocalEmbeddingAdapter",
    "LocalEmbeddingConfig",
    "OpenAIEmbeddingAdapter",
    "OpenAIEmbeddingConfig",
    "VoyageEmbeddingAdapter",
    "VoyageEmbeddingConfig",
]
