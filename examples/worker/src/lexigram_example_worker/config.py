"""Worker configuration using the Lexigram BaseConfig pattern."""

from __future__ import annotations

from dataclasses import dataclass

from lexigram.config import BaseConfig
from lexigram.validation import Field


@dataclass(init=False)
class WorkerConfig(BaseConfig):
    """Top-level configuration for the background worker process.

    All fields can be overridden via environment variables.  The
    :class:`~lexigram.config.base.BaseConfig` base class resolves values from
    YAML files and ``LEX_*`` environment variables automatically.

    Attributes:
        queue_driver: Queue backend to use (``memory``, ``redis``, ``rabbitmq``).
        redis_url: Redis connection URL (used when ``queue_driver="redis"``).
        rabbitmq_url: RabbitMQ AMQP URL (used when ``queue_driver="rabbitmq"``).
        concurrency: Number of concurrent task worker coroutines.
        dlq_max_size: Maximum entries retained in the dead letter queue.
        dlq_retention_hours: Hours before DLQ entries expire and are purged.
        scheduler_enabled: Whether to start the cron-based job scheduler.
        cleanup_cron: Cron expression for the periodic cleanup task.
    """

    queue_driver: str = Field(default="memory", description="Queue backend driver.")
    redis_url: str = Field(
        default="redis://localhost:26379/0",
        description="Redis connection URL.",
    )
    rabbitmq_url: str = Field(
        default="amqp://guest:guest@localhost/",
        description="RabbitMQ AMQP URL.",
    )
    concurrency: int = Field(
        default=4,
        description="Concurrent task worker coroutines.",
    )
    dlq_max_size: int = Field(
        default=10_000,
        description="Dead letter queue maximum entry count.",
    )
    dlq_retention_hours: float = Field(
        default=168.0,
        description="Hours to retain DLQ entries before automatic purge.",
    )
    scheduler_enabled: bool = Field(
        default=True,
        description="Enable the cron-based job scheduler.",
    )
    cleanup_cron: str = Field(
        default="0 3 * * *",
        description="Cron expression for the periodic record-cleanup task.",
    )


__all__ = ["WorkerConfig"]
