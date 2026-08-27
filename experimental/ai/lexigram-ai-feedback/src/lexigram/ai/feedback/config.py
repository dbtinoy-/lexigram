"""Feedback configuration for Lexigram."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, cast

from lexigram.ai.feedback import constants as const
from lexigram.config import (
    BaseConfig,
)
from lexigram.contracts.core.config import ConfigIssue, Environment
from lexigram.validation import ConfigDict, Field


@dataclass(init=False)
class FeedbackConfig(BaseConfig):
    """Configuration for AI feedback collection.

    Loaded from the ``ai_feedback:`` key in application.yaml, with environment
    variable overrides via ``LEX_AI_FEEDBACK__*`` prefix.
    """

    config_section: ClassVar[str] = "ai_feedback"

    model_config: ClassVar[ConfigDict] = cast(
        "ConfigDict",
        {
            "env_prefix": const.ENV_PREFIX,
            "env_nested_delimiter": const.ENV_NESTED_DELIMITER,
            "extra": "ignore",
        },
    )

    enabled: bool = Field(
        default=True, description="Master on/off switch for all feedback collection"
    )
    name: str = "ai_feedback"
    env: Environment | None = Field(None, description="Deployment environment")
    async_processing: bool = Field(
        default=True,
        description="Process feedback handlers asynchronously in the background",
    )
    store_raw_payloads: bool = Field(
        default=False,
        description="Persist raw incoming feedback payloads for auditing",
    )

    def validate_for_environment(
        self, env: Environment | None = None
    ) -> list[ConfigIssue]:
        """Check config is safe for the target environment."""
        return []


__all__ = ["FeedbackConfig"]
