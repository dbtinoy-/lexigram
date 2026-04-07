"""Configuration for the OpenAI-compatible embedding client."""

from __future__ import annotations

from typing import ClassVar, Literal, cast

from lexigram.config.base import BaseConfig
from lexigram.validation import ConfigDict, Field

ENV_PREFIX: str = "LEX_VECTOR__EMBEDDING__"


class EmbeddingClientConfig(BaseConfig):
    """Configuration for the OpenAI-compatible embedding HTTP client.

    Reads from ``LEX_VECTOR__EMBEDDING__*`` environment variables.
    Supports any backend that implements the OpenAI ``/v1/embeddings`` API:
    text-embeddings-inference (local), LM Studio, OpenAI, Cohere, FastEmbed, etc.

    Example::

        # Local FastEmbed (uses "texts" field):
        LEX_VECTOR__EMBEDDING__API_BASE=http://fastembed:8000
        LEX_VECTOR__EMBEDDING__MODEL=BAAI/bge-small-en-v1.5
        LEX_VECTOR__EMBEDDING__DIMENSION=384
        LEX_VECTOR__EMBEDDING__FORMAT=fastembed

        # Local (docker-compose, infinity embedding server):
        LEX_VECTOR__EMBEDDING__API_BASE=http://fastembed
        LEX_VECTOR__EMBEDDING__MODEL=nomic-ai/nomic-embed-text-v1.5
        LEX_VECTOR__EMBEDDING__DIMENSION=768

        # Production (OpenAI — uses /v1/embeddings):
        LEX_VECTOR__EMBEDDING__API_BASE=https://api.openai.com/v1
        LEX_VECTOR__EMBEDDING__MODEL=text-embedding-3-small
        LEX_VECTOR__EMBEDDING__DIMENSION=1536
        LEX_VECTOR__EMBEDDING__API_KEY=sk-...
        LEX_VECTOR__EMBEDDING__FORMAT=openai
    """

    model_config: ClassVar[ConfigDict] = cast(
        "ConfigDict",
        {
            "env_prefix": ENV_PREFIX,
            "env_nested_delimiter": "__",
            "extra": "ignore",
        },
    )

    api_base: str = Field(
        default="http://fastembed",
        description="Base URL of the embedding API. The client appends '/embeddings' to this URL.",
    )
    model: str = Field(
        default="nomic-ai/nomic-embed-text-v1.5",
        description="Embedding model identifier passed to the API.",
    )
    dimension: int = Field(
        default=768,
        description=(
            "Expected output vector dimension. Must match the model "
            "(768 for nomic-embed-text-v1.5, 1536 for text-embedding-ada-002)."
        ),
    )
    timeout: float = Field(
        default=30.0,
        description="HTTP request timeout in seconds.",
    )
    batch_size: int = Field(
        default=64,
        description="Maximum number of texts per embedding API request.",
    )
    api_key: str | None = Field(
        default=None,
        description="API key sent as Bearer token (required for OpenAI and most cloud providers).",
    )
    format: Literal["openai", "fastembed", "cohere"] = Field(
        default="openai",
        description=(
            "API payload format. 'openai' uses {'input': [...]}, "
            "'fastembed' uses {'texts': [...]}, 'cohere' uses {'texts': [...]}."
        ),
    )


__all__ = ["EmbeddingClientConfig"]
