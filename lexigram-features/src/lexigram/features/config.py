"""Configuration model for the feature-flag subsystem."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from lexigram.config.base import BaseConfig
from lexigram.features.constants import (
    DEFAULT_CACHE_TTL,
    DEFAULT_ENABLED,
    ENV_NESTED_DELIMITER,
)
from lexigram.features.constants import (
    ENV_PREFIX as FLAG_ENV_PREFIX,
)
from lexigram.validation import ConfigDict, Field


@dataclass(init=False)
class FeatureFlagsConfig(BaseConfig):
    """Runtime configuration for the feature flag DI provider.

    Values here control the default behaviour of the container-registered
    :class:`~lexigram.feature_flags.manager.FlagManager` instance.
    """

    config_section: ClassVar[str] = "features"

    model_config: ClassVar[ConfigDict] = ConfigDict(  # type: ignore[typeddict-unknown-key]
        env_prefix="LEX_FEATURES__",
        env_nested_delimiter=ENV_NESTED_DELIMITER,
        extra="ignore",
    )

    enabled: bool = Field(
        default=True, description="Enable the feature flags subsystem"
    )

    cache_ttl: int = Field(
        default=DEFAULT_CACHE_TTL,
        ge=0,
        description="Seconds to cache flag evaluations (0 = disabled).",
    )
    default_enabled: bool = Field(
        default=DEFAULT_ENABLED,
        description="Default value when a flag is not found in the provider.",
    )
    flag_env_prefix: str = Field(
        default=FLAG_ENV_PREFIX,
        description="Env var prefix used by EnvProvider when reading flag values.",
    )
    initial_flags: dict[str, bool] = Field(
        default_factory=dict,
        description="Seed flags for the in-memory provider (name -> enabled).",
    )


__all__ = ["FeatureFlagsConfig"]
