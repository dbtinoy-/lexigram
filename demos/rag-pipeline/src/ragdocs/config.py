"""Demo-specific configuration models.

Convention followed: **Config model** — ``RagDocsConfig`` extends
``BaseConfig`` (stdlib dataclass, NOT pydantic).  Each field uses
``Field()`` with a description and default value.  The framework
validates the YAML section against this model at boot time.

For full reference see:
- ``lexigram.config.BaseConfig`` — base config class
- ``lexigram.validation.Field`` — field descriptor with validation
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from lexigram.config import BaseConfig
from lexigram.contracts.core.config import Environment
from lexigram.validation import ConfigDict, Field


@dataclass(init=False)
class RagDocsConfig(BaseConfig):
    """Root configuration for the rag-pipeline demo.

    Maps 1:1 to the ``ragdocs:`` section in ``application.yaml``.
    The framework merges YAML values + ``LEX_RAGDOCS__*`` env overrides
    into this model at boot time.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")
    config_section: ClassVar[str] = "ragdocs"
    name: str = "ragdocs"
    enabled: bool = True
    env: Environment | None = Field(None, description="Deployment environment")

    collection_name: str = Field(
        default="documents",
        description="Vector collection name",
    )
    embedding_dimension: int = Field(
        default=128,
        description="Embedding vector dimension",
    )
    chunk_size: int = Field(
        default=500,
        description="Document chunk size in characters",
    )
    top_k: int = Field(
        default=5,
        description="Number of results to retrieve",
    )

    # Uncomment to add more config fields:
    # similarity_threshold: float = Field(
    #     default=0.7,
    #     description="Minimum similarity score",
    # )
    # max_results: int = Field(
    #     default=10,
    #     description="Maximum results per query",
    # )
    # embedding_model: str = Field(
    #     default="default",
    #     description="Embedding model name",
    # )


__all__ = ["RagDocsConfig"]
