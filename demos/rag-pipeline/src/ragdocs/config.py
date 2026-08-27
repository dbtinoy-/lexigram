"""Demo-specific configuration models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from lexigram.config import BaseConfig
from lexigram.validation import ConfigDict, Field


@dataclass(init=False)
class RagDocsConfig(BaseConfig):
    """Root configuration for the rag-pipeline demo."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")
    config_section: ClassVar[str | None] = "ragdocs"

    collection_name: str = Field(default="documents", description="Vector collection name")
    embedding_dimension: int = Field(default=128, description="Embedding dimension")
    chunk_size: int = Field(default=500, description="Document chunk size in characters")
    top_k: int = Field(default=5, description="Number of results to retrieve")


__all__ = ["RagDocsConfig"]
