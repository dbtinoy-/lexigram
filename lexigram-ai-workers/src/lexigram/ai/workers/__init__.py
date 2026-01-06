"""
Background workers for lexigram-intelligence.

This module provides background processing capabilities for:
- Document ingestion and processing
- Batch embedding generation
- Scheduled maintenance tasks
- Failed task recovery (Dead Letter Queue)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lexigram.ai.workers.batch_embedding import (
        BatchEmbeddingJob,
        BatchEmbeddingProgress,
        BatchEmbeddingResult,
        BatchEmbeddingWorker,
    )
    from lexigram.ai.workers.config import WorkersConfig
    from lexigram.ai.workers.constants import (
        DEFAULT_BASE_BACKOFF,
        DEFAULT_CHECK_INTERVAL,
        DEFAULT_MAX_RETRIES,
        DEFAULT_TASK_TIMEOUT,
        MAX_BACKOFF_SECONDS,
        MAX_HISTORY_SIZE,
    )
    from lexigram.ai.workers.di.provider import WorkersProvider
    from lexigram.ai.workers.dlq.worker import DeadLetterQueueWorker, ErrorClassifier
    from lexigram.ai.workers.document_ingestion import (
        DocumentIngestionJob,
        DocumentIngestionWorker,
        IngestionProgress,
        IngestionResult,
    )
    from lexigram.ai.workers.exceptions import DLQError, MaintenanceError, WorkerError
    from lexigram.ai.workers.hooks import (
        WorkerJobCompletedHook,
        WorkerJobStartedHook,
        WorkerMaintenanceRunHook,
    )
    from lexigram.ai.workers.maintenance.worker import MaintenanceWorker
    from lexigram.ai.workers.module import WorkersModule
    from lexigram.ai.workers.types import (
        DLQAction,
        DLQItem,
        DLQStats,
        FailureCategory,
        MaintenanceResult,
        MaintenanceStatus,
        MaintenanceTask,
        MaintenanceTaskType,
    )

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "BatchEmbeddingJob": ("lexigram.ai.workers.batch_embedding", "BatchEmbeddingJob"),
    "BatchEmbeddingProgress": (
        "lexigram.ai.workers.batch_embedding",
        "BatchEmbeddingProgress",
    ),
    "BatchEmbeddingResult": (
        "lexigram.ai.workers.batch_embedding",
        "BatchEmbeddingResult",
    ),
    "BatchEmbeddingWorker": (
        "lexigram.ai.workers.batch_embedding",
        "BatchEmbeddingWorker",
    ),
    "DEFAULT_BASE_BACKOFF": ("lexigram.ai.workers.constants", "DEFAULT_BASE_BACKOFF"),
    "DEFAULT_CHECK_INTERVAL": (
        "lexigram.ai.workers.constants",
        "DEFAULT_CHECK_INTERVAL",
    ),
    "DEFAULT_MAX_RETRIES": ("lexigram.ai.workers.constants", "DEFAULT_MAX_RETRIES"),
    "DEFAULT_TASK_TIMEOUT": ("lexigram.ai.workers.constants", "DEFAULT_TASK_TIMEOUT"),
    "DLQAction": ("lexigram.ai.workers.types", "DLQAction"),
    "DLQError": ("lexigram.ai.workers.exceptions", "DLQError"),
    "DLQItem": ("lexigram.ai.workers.types", "DLQItem"),
    "DLQStats": ("lexigram.ai.workers.types", "DLQStats"),
    "DeadLetterQueueWorker": (
        "lexigram.ai.workers.dlq.worker",
        "DeadLetterQueueWorker",
    ),
    "DocumentIngestionJob": (
        "lexigram.ai.workers.document_ingestion",
        "DocumentIngestionJob",
    ),
    "DocumentIngestionWorker": (
        "lexigram.ai.workers.document_ingestion",
        "DocumentIngestionWorker",
    ),
    "ErrorClassifier": ("lexigram.ai.workers.dlq.worker", "ErrorClassifier"),
    "FailureCategory": ("lexigram.ai.workers.types", "FailureCategory"),
    "IngestionProgress": (
        "lexigram.ai.workers.document_ingestion",
        "IngestionProgress",
    ),
    "IngestionResult": ("lexigram.ai.workers.document_ingestion", "IngestionResult"),
    "MaintenanceError": ("lexigram.ai.workers.exceptions", "MaintenanceError"),
    "MaintenanceResult": ("lexigram.ai.workers.types", "MaintenanceResult"),
    "WorkerJobCompletedHook": (
        "lexigram.ai.workers.hooks",
        "WorkerJobCompletedHook",
    ),
    "WorkerJobStartedHook": (
        "lexigram.ai.workers.hooks",
        "WorkerJobStartedHook",
    ),
    "WorkerMaintenanceRunHook": (
        "lexigram.ai.workers.hooks",
        "WorkerMaintenanceRunHook",
    ),
    "MaintenanceStatus": ("lexigram.ai.workers.types", "MaintenanceStatus"),
    "MaintenanceTask": ("lexigram.ai.workers.types", "MaintenanceTask"),
    "MaintenanceTaskType": ("lexigram.ai.workers.types", "MaintenanceTaskType"),
    "MaintenanceWorker": (
        "lexigram.ai.workers.maintenance.worker",
        "MaintenanceWorker",
    ),
    "MAX_BACKOFF_SECONDS": ("lexigram.ai.workers.constants", "MAX_BACKOFF_SECONDS"),
    "MAX_HISTORY_SIZE": ("lexigram.ai.workers.constants", "MAX_HISTORY_SIZE"),
    "WorkerError": ("lexigram.ai.workers.exceptions", "WorkerError"),
    "WorkersConfig": ("lexigram.ai.workers.config", "WorkersConfig"),
    "WorkersModule": ("lexigram.ai.workers.module", "WorkersModule"),
    "WorkersProvider": ("lexigram.ai.workers.di.provider", "WorkersProvider"),
}

__all__ = list(_LAZY_IMPORTS)


def __getattr__(name: str) -> object:
    """Lazy-load public symbols on first access."""
    if name in _LAZY_IMPORTS:
        import importlib

        module_path, attr = _LAZY_IMPORTS[name]
        mod = importlib.import_module(module_path)
        value = getattr(mod, attr)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """Expose lazy-loaded names for tab completion and dir()."""
    return list(_LAZY_IMPORTS)
