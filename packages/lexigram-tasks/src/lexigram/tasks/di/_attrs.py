"""Shared attribute surface for TaskProvider mixins."""

from __future__ import annotations

from typing import Any


class _TaskAttrsMixin:
    """Attribute contract shared by all TaskProvider mixins."""
    _backend_registry: Any
    _background_tasks: Any
    _config: Any
    _container: Any
    _middleware_pipeline: Any
    _queue_services: Any
    _result_store: Any
    _enqueue_job: Any
    enable_scheduler: Any
    logger: Any
    name: Any
    queue: Any
    registry: Any
    scheduler: Any
    scheduler_task: Any
    worker_count: Any
    worker_pool: Any
