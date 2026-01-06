"""AI example application configuration."""

from __future__ import annotations

from dataclasses import dataclass

from lexigram.config import BaseConfig
from lexigram.validation import Field


@dataclass(init=False)
class AIConfig(BaseConfig):
    """Top-level configuration for the AI pipeline example.

    All fields can be overridden via environment variables.  The
    :class:`~lexigram.config.base.BaseConfig` base class resolves values from
    YAML files and ``LEX_*`` / ``AI_*`` environment variables automatically.

    Attributes:
        llm_driver: LLM backend to use (``stub``, ``openai``, ``anthropic``).
        llm_model: Default model identifier forwarded to the LLM client.
        llm_temperature: Sampling temperature for completions.
        llm_max_tokens: Maximum output tokens per completion.
        vector_driver: Vector store backend (``memory``, ``qdrant``).
        qdrant_url: Qdrant base URL (used when ``vector_driver="qdrant"``).
        qdrant_collection: Qdrant collection name.
        rag_top_k: Number of documents to retrieve per RAG query.
        rag_score_threshold: Minimum relevance score for retrieved documents.
    """

    llm_driver: str = Field(
        default="stub",
        description="LLM backend driver (stub | openai | anthropic).",
    )
    llm_model: str = Field(
        default="gpt-4o",
        description="Default model identifier.",
    )
    llm_temperature: float = Field(
        default=0.7,
        description="Sampling temperature for completions.",
    )
    llm_max_tokens: int = Field(
        default=2048,
        description="Maximum output tokens per completion.",
    )
    vector_driver: str = Field(
        default="memory",
        description="Vector store backend driver (memory | qdrant).",
    )
    qdrant_url: str = Field(
        default="http://localhost:26333",
        description="Qdrant base URL.",
    )
    qdrant_collection: str = Field(
        default="lexigram_example",
        description="Qdrant collection name.",
    )
    rag_top_k: int = Field(
        default=5,
        description="Number of documents to retrieve per RAG query.",
    )
    rag_score_threshold: float = Field(
        default=0.5,
        description="Minimum relevance score for retrieved documents.",
    )


__all__ = ["AIConfig"]
