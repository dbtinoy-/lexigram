"""Evaluation configuration for the Lexigram framework."""

from __future__ import annotations

from typing import ClassVar, cast

from lexigram.ai.evaluation import constants as const
from lexigram.config.base import BaseConfig
from lexigram.validation import ConfigDict, Field

ENV_PREFIX: str = const.ENV_PREFIX
ENV_NESTED_DELIMITER: str = const.ENV_NESTED_DELIMITER


class EvaluationConfig(BaseConfig):
    """Configuration for the evaluation subsystem.

    Attributes:
        enabled: Enable the AI evaluation subsystem.
        default_threshold: Default score threshold for passing evaluations.
        embedding_model: Model to use for embedding-based evaluations.
        include_metadata: Whether to include metadata in run reports.
        max_samples: Maximum number of samples per evaluation run.
        max_retries: Maximum retries for failed evaluations.
        timeout_seconds: Timeout for evaluation execution in seconds.

    Example::

        config = EvaluationConfig(
            default_threshold=0.9,
            embedding_model="text-embedding-3-large"
        )
    """

    config_section: ClassVar[str] = "ai_evaluation"

    model_config: ClassVar[ConfigDict] = cast(
        "ConfigDict",
        {
            "env_prefix": ENV_PREFIX,
            "env_nested_delimiter": ENV_NESTED_DELIMITER,
            "extra": "ignore",
        },
    )

    enabled: bool = Field(
        default=True, description="Enable the AI evaluation subsystem"
    )

    experiment_dir: str | None = Field(
        default=None,
        description="Base directory for experiment tracking and checkpoint artifacts",
    )

    default_seed: int | None = Field(
        default=None,
        ge=0,
        description="Default seed for reproducible experiment runs",
    )

    default_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Default score threshold for passing evaluations",
    )

    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="Model to use for embedding-based evaluations",
    )

    include_metadata: bool = Field(
        default=True,
        description="Whether to include metadata in run reports",
    )

    max_samples: int | None = Field(
        default=None,
        ge=1,
        description="Maximum number of samples per evaluation run",
    )

    max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum retries for failed evaluations",
    )

    timeout_seconds: int = Field(
        default=30,
        ge=1,
        description="Timeout for evaluation execution in seconds",
    )


__all__ = ["ENV_NESTED_DELIMITER", "ENV_PREFIX", "EvaluationConfig"]
