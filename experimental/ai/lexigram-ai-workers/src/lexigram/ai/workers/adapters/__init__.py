"""Task queue and pipeline adapters for optional integrations.

Bridges lexigram-intelligence workers with external task queues, the RAG
pipeline, and document loader registries.
"""

from __future__ import annotations

from lexigram.ai.workers.adapters.loader_worker import LoaderWorkerBridge
from lexigram.ai.workers.adapters.rag_adapter import (
    IngestionError,
    IngestionReport,
    RAGIngestionAdapter,
)
from lexigram.ai.workers.adapters.tasks_adapter import (
    HAS_LEX_TASKS,
    LexigramTasksAdapter,
)

__all__ = [
    "HAS_LEX_TASKS",
    "IngestionError",
    "IngestionReport",
    "LexigramTasksAdapter",
    "LoaderWorkerBridge",
    "RAGIngestionAdapter",
]
