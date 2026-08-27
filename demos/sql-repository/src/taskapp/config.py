"""Demo-specific configuration models.

Convention followed: **Config model** — ``TaskAppConfig`` extends
``BaseConfig`` (stdlib dataclass, NOT pydantic).  Each field uses
``Field()`` with a description and default value.  The framework
validates the YAML section against this model at boot time.

For full reference see:
- ``lexigram.config.BaseConfig`` — base config class
- ``lexigram.validation.Field`` — field descriptor with validation
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from lexigram.config import BaseConfig
from lexigram.validation import ConfigDict, Field


@dataclass(init=False)
class TaskAppConfig(BaseConfig):
    """Root configuration for the sql-repository demo.

    Maps 1:1 to the ``task_app:`` section in ``application.yaml``.
    The framework merges YAML values + ``LEX_TASK_APP__*`` env overrides
    into this model at boot time.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")
    config_section: ClassVar[str | None] = "task_app"
    name: str = "task_app"
    enabled: bool = True

    project_name: str = Field(
        default="Task Manager",
        description="Display name for the project",
    )

    # Uncomment to add more config fields:
    # max_users: int = Field(
    #     default=100,
    #     description="Maximum number of users",
    # )
    # max_projects: int = Field(
    #     default=50,
    #     description="Maximum number of projects",
    # )
    # max_tasks_per_project: int = Field(
    #     default=200,
    #     description="Maximum tasks per project",
    # )


__all__ = ["TaskAppConfig"]
