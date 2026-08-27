"""Demo-specific configuration models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from lexigram.config import BaseConfig
from lexigram.validation import ConfigDict, Field


@dataclass(init=False)
class QueueWorkerConfig(BaseConfig):
    """Root configuration for the queue-worker demo."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")
    config_section: ClassVar[str | None] = "queueworker"

    queue_name: str = Field(default="tasks", description="Queue name")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    batch_size: int = Field(default=10, description="Batch processing size")


__all__ = ["QueueWorkerConfig"]
