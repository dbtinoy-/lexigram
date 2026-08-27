"""FlagManager configuration dataclass."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from lexigram.config.base import BaseConfig
from lexigram.validation import ConfigDict, Field


@dataclass(init=False)
class ManagerConfig(BaseConfig):
    """Configuration for :class:`~lexigram.features.manager.FlagManager` instances."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    cache_ttl: int = Field(default=300)
    """Seconds to cache evaluations (0 = disabled)."""

    default_enabled: bool = Field(default=False)
    """Return value when a flag is not found in the provider."""


__all__ = ["ManagerConfig"]
