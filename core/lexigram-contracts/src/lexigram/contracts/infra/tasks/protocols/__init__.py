"""Task and job queue protocol class definitions."""

from __future__ import annotations

from lexigram.contracts.infra.tasks.protocols.idempotency import (
    IdempotencyManagerProtocol as IdempotencyManagerProtocol,
)
from lexigram.contracts.infra.tasks.protocols.idempotency import (
    IdempotentTaskManagerProtocol as IdempotentTaskManagerProtocol,
)
from lexigram.contracts.infra.tasks.protocols.queue import DLQProtocol as DLQProtocol
from lexigram.contracts.infra.tasks.protocols.queue import JobProtocol as JobProtocol
from lexigram.contracts.infra.tasks.protocols.queue import (
    JobTemplateProtocol as JobTemplateProtocol,
)
from lexigram.contracts.infra.tasks.protocols.queue import (
    TaskExecutorProtocol as TaskExecutorProtocol,
)
from lexigram.contracts.infra.tasks.protocols.queue import (
    TaskManagerProtocol as TaskManagerProtocol,
)
from lexigram.contracts.infra.tasks.protocols.queue import (
    TaskProviderProtocol as TaskProviderProtocol,
)
from lexigram.contracts.infra.tasks.protocols.queue import (
    TaskQueueProtocol as TaskQueueProtocol,
)
from lexigram.contracts.infra.tasks.protocols.queue import (
    TaskWorkerProtocol as TaskWorkerProtocol,
)

__all__ = [
    "DLQProtocol",
    "IdempotencyManagerProtocol",
    "IdempotentTaskManagerProtocol",
    "JobProtocol",
    "JobTemplateProtocol",
    "TaskExecutorProtocol",
    "TaskProviderProtocol",
    "TaskQueueProtocol",
    "TaskWorkerProtocol",
]
