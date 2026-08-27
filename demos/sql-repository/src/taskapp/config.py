"""Demo-specific configuration models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from lexigram.config import BaseConfig
from lexigram.validation import ConfigDict, Field


@dataclass(init=False)
class TaskAppConfig(BaseConfig):
    """Root configuration for the sql-repository demo."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")
    config_section: ClassVar[str | None] = "task_app"

    project_name: str = Field(
        default="Task Manager",
        description="Display name for the project",
    )


__all__ = ["TaskAppConfig"]
