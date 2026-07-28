"""Framework integration for lexigram-tasks."""

from __future__ import annotations

from lexigram.tasks.di.factories import (
    create_memory_task_provider,
    create_provider_from_config,
    create_rabbitmq_task_provider,
    create_redis_task_provider,
)
from lexigram.tasks.di.provider import TaskProvider

__all__ = [
    "TaskProvider",
    "create_memory_task_provider",
    "create_provider_from_config",
    "create_rabbitmq_task_provider",
    "create_redis_task_provider",
]
