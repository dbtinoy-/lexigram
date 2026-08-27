"""Demo-specific configuration models.

Convention followed: **Config model** — ``QueueWorkerConfig`` extends
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
class QueueWorkerConfig(BaseConfig):
    """Root configuration for the queue-worker demo.

    Maps 1:1 to the ``queueworker:`` section in ``application.yaml``.
    The framework merges YAML values + ``LEX_QUEUEWORKER__*`` env overrides
    into this model at boot time.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")
    config_section: ClassVar[str | None] = "queueworker"

    queue_name: str = Field(
        default="tasks",
        description="Name of the default queue",
    )
    max_retries: int = Field(
        default=3,
        description="Maximum retry attempts per message",
    )
    batch_size: int = Field(
        default=10,
        description="Messages to process per batch",
    )

    # Uncomment to add more config fields:
    # dead_letter_queue: str = Field(
    #     default="tasks.dlq",
    #     description="Dead letter queue name",
    # )
    # message_ttl: int = Field(
    #     default=3600,
    #     description="Message TTL in seconds",
    # )
    # visibility_timeout: int = Field(
    #     default=30,
    #     description="Visibility timeout in seconds",
    # )


__all__ = ["QueueWorkerConfig"]
