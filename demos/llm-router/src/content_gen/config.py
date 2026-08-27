"""Demo-specific configuration models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from lexigram.config import BaseConfig
from lexigram.validation import ConfigDict, Field


@dataclass(init=False)
class ContentGenConfig(BaseConfig):
    """Root configuration for the llm-router demo."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")
    config_section: ClassVar[str | None] = "content_gen"

    default_style: str = Field(
        default="professional",
        description="Default writing style for content generation",
    )
    max_retries: int = Field(default=3, description="Maximum retry attempts")


__all__ = ["ContentGenConfig"]
