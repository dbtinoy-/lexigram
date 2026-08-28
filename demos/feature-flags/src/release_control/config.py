"""Typed configuration for the Release Control Lab."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from lexigram.config import BaseConfig
from lexigram.contracts.core.config import Environment
from lexigram.validation import ConfigDict, Field


@dataclass(init=False)
class ReleaseControlConfig(BaseConfig):
    """Small demo-owned section; flag definitions belong to Lexigram."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")
    config_section: ClassVar[str] = "release_control"
    name: str = "release_control"
    enabled: bool = True
    env: Environment | None = Field(None, description="Deployment environment")
    default_actor: str = Field(
        default="release-operator",
        description="Actor label used for browser override changes",
    )


__all__ = ["ReleaseControlConfig"]
