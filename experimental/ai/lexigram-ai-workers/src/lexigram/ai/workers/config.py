"""Worker configuration for the Lexigram framework."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, cast

from lexigram.ai.workers.constants import ENV_NESTED_DELIMITER, ENV_PREFIX
from lexigram.config.base import BaseConfig
from lexigram.contracts.core.config import Environment
from lexigram.validation import ConfigDict, Field

if TYPE_CHECKING:
    from lexigram.contracts.core.config import ConfigIssue, Environment


@dataclass(init=False)
class WorkersConfig(BaseConfig):
    """Configuration for AI background workers.

    Loaded from the ``ai_workers:`` key in application.yaml, with environment
    variable overrides via ``LEX_AI_WORKERS__*`` prefix.
    """

    config_section: ClassVar[str] = "ai_workers"

    model_config: ClassVar[ConfigDict] = cast(
        "ConfigDict",
        {
            "env_prefix": ENV_PREFIX,
            "env_nested_delimiter": ENV_NESTED_DELIMITER,
            "extra": "ignore",
        },
    )

    enabled: bool = Field(
        default=True, description="Master on/off switch for all background workers"
    )
    name: str = "ai_workers"
    env: Environment | None = Field(None, description="Deployment environment")
    batch_embedding_concurrency: int = Field(
        default=3,
        ge=1,
        description="Concurrency level for batch embedding execution",
    )
    document_ingestion_concurrency: int = Field(
        default=3,
        ge=1,
        description="Concurrency level for document parsing and chunking",
    )
    enable_maintenance: bool = Field(
        default=True,
        description="Enable vector store and cache maintenance tasks",
    )
    dlq_check_interval: int = Field(
        default=60,
        ge=1,
        description="Interval in seconds for DLQ recovery sweeps",
    )

    def validate_for_environment(
        self,
        env: Environment | None = None,
    ) -> list[ConfigIssue]:
        """Check config is safe for the target environment."""
        return []


__all__ = ["WorkersConfig"]
