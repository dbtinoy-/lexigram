"""Observability configuration for Lexigram."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, cast

from lexigram.ai.observability import constants as const
from lexigram.config import (
    BaseConfig,
)
from lexigram.contracts.core.config import ConfigIssue, Environment
from lexigram.validation import ConfigDict, Field


@dataclass(init=False)
class ObservabilityConfig(BaseConfig):
    """Configuration for AI observability.

    Loaded from the ``ai_observability:`` key in application.yaml, with environment
    variable overrides via ``LEX_AI_OBSERVABILITY__*`` prefix.
    """

    config_section: ClassVar[str] = "ai_observability"

    model_config: ClassVar[ConfigDict] = cast(
        "ConfigDict",
        {
            "env_prefix": const.ENV_PREFIX,
            "env_nested_delimiter": const.ENV_NESTED_DELIMITER,
            "extra": "ignore",
        },
    )

    enabled: bool = Field(
        default=True, description="Master on/off switch for all observability"
    )
    metrics_enabled: bool = Field(default=True, description="Enable metrics collection")
    tracing_enabled: bool = Field(
        default=True, description="Enable distributed tracing"
    )
    health_checks_enabled: bool = Field(
        default=True,
        description="Enable background health checking for AI components",
    )

    def validate_for_environment(
        self, env: Environment | None = None
    ) -> list[ConfigIssue]:
        """Check config is safe for the target environment."""
        issues: list[ConfigIssue] = []

        if env == Environment.PRODUCTION:
            if not self.tracing_enabled:
                issues.append(
                    ConfigIssue(
                        severity="warning",
                        field="tracing_enabled",
                        message="Distributed tracing disabled in production",
                        suggestion=(
                            f"Set {const.ENV_PREFIX}TRACING_ENABLED=true for "
                            "production observability."
                        ),
                    )
                )
            if not self.metrics_enabled:
                issues.append(
                    ConfigIssue(
                        severity="warning",
                        field="metrics_enabled",
                        message="Metrics collection disabled in production",
                        suggestion=(
                            f"Set {const.ENV_PREFIX}METRICS_ENABLED=true to collect "
                            "operational metrics."
                        ),
                    )
                )

        return issues


__all__ = ["ObservabilityConfig"]
