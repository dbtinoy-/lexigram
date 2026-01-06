"""Worker pool and execution management

This module provides worker management for task processing,
including health monitoring and statistics.
"""

from __future__ import annotations

from lexigram.tasks.execution.health import TaskHealth
from lexigram.tasks.execution.metrics import TaskMetricsCollector
from lexigram.tasks.execution.pool import WorkerPool
from lexigram.tasks.execution.registry import HandlerRegistry
from lexigram.tasks.execution.worker import (
    TaskWorker,
    TaskWorkerServices,
    WorkerJobStats,
)

__all__ = [
    "HandlerRegistry",
    # Metrics
    "TaskHealth",
    "TaskMetricsCollector",
    "TaskWorker",
    "TaskWorkerServices",
    "WorkerJobStats",
    "WorkerPool",
]
