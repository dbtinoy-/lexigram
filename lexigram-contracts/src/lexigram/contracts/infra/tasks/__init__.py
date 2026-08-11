"""Task and job queue protocols."""

from __future__ import annotations

from lexigram.contracts.infra.tasks.enums import JobStatus, OnErrorPolicy
from lexigram.contracts.infra.tasks.exceptions import TaskQueueError
from lexigram.contracts.infra.tasks.idempotency import (
    IdempotencyResult,
    IdempotencyResultStatus,
)
from lexigram.contracts.infra.tasks.progress import (
    ProgressSnapshot,
    ProgressStatus,
    ProgressTrackerProtocol,
)
from lexigram.contracts.infra.tasks.protocols import (
    DLQProtocol,
    IdempotencyManagerProtocol,
    IdempotentTaskManagerProtocol,
    JobProtocol,
    JobTemplateProtocol,
    TaskExecutorProtocol,
    TaskManagerProtocol,
    TaskProviderProtocol,
    TaskQueueProtocol,
    TaskWorkerProtocol,
)

__all__ = [
    "DLQProtocol",
    "IdempotencyManagerProtocol",
    "IdempotencyResult",
    "IdempotencyResultStatus",
    "IdempotentTaskManagerProtocol",
    "JobProtocol",
    "JobStatus",
    "JobTemplateProtocol",
    "OnErrorPolicy",
    "ProgressSnapshot",
    "ProgressStatus",
    "ProgressTrackerProtocol",
    "TaskExecutorProtocol",
    "TaskManagerProtocol",
    "TaskProviderProtocol",
    "TaskQueueError",
    "TaskQueueProtocol",
    "TaskWorkerProtocol",
]
