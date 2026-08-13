---
title: lexigram-ai-workers How-Tos
description: Task-oriented recipes for common worker operations
---

## Submit a Batch Embedding Job

```python
from lexigram.ai.workers.batch_embedding import BatchEmbeddingWorker
from lexigram.contracts.ai.rag import ChunkProtocol


worker = await container.resolve(BatchEmbeddingWorker)

chunks: list[ChunkProtocol] = [
    ChunkProtocol(text="Document one", metadata={"source": "file1.pdf"}),
    ChunkProtocol(text="Document two", metadata={"source": "file2.pdf"}),
]

job_id = await worker.embed_batch(
    chunks=chunks,
    collection_name="my-docs",
    model_name="text-embedding-ada-002",
    batch_size=50,
)
```

## Track Embedding Progress

```python
progress = await worker.get_progress(job_id)
if progress:
    print(f"Status: {progress.status.value}")
    print(f"Progress: {progress.progress_percent:.1f}%")
    print(f"Cache hit rate: {progress.cache_hit_rate:.1f}%")
```

## Ingest a Document

```python
from pathlib import Path

from lexigram.ai.workers.document_ingestion import DocumentIngestionWorker


worker = await container.resolve(DocumentIngestionWorker)

job_id = await worker.ingest_document(
    document_id="doc-001",
    file_path=Path("/data/reports/Q1-2026.pdf"),
    collection_name="reports",
    metadata={"department": "finance"},
)

progress = await worker.get_progress(job_id)
```

## Register a Maintenance Task

```python
from lexigram.ai.workers.maintenance.worker import MaintenanceWorker
from lexigram.ai.workers.types import MaintenanceTaskType


maint = await container.resolve(MaintenanceWorker)

maint.register_task(
    name="optimize_vectors",
    task_type=MaintenanceTaskType.INDEX_OPTIMIZATION,
    handler=lambda: vector_store.optimize_indexes(),
    interval_seconds=3600,
    timeout=300.0,
)

# Run a task immediately
result = await maint.run_task_now("optimize_vectors")
print(f"{result.status.value}: {result.duration_seconds:.2f}s")
```

## Handle Failed Jobs with DLQ

```python
from lexigram.ai.workers.dlq.worker import DeadLetterQueueWorker
from lexigram.ai.workers.types import DLQItem


dlq = await container.resolve(DeadLetterQueueWorker)

# Add a failed job
await dlq.add_failed_job(job, error="Connection timeout")

# Check stats
stats = await dlq.get_stats()
print(f"Total: {stats.total_items}, Permanent: {stats.permanent_failures}")

# Manually retry
await dlq.retry_item("job-42")

# Set notification handler for permanent failures
async def alert(item: DLQItem) -> None:
    await send_pagerduty(f"Permanent failure: {item.job_id}")

dlq.set_notification_handler(alert)
```

## Clear the Embedding Cache

```python
worker = await container.resolve(BatchEmbeddingWorker)
await worker.clear_cache()
```

## Use WorkersModule.stub() in Tests

```python
import pytest
from lexigram.ai.workers import WorkersModule


@pytest.fixture
def workers_module() -> WorkersModule:
    # No background scheduler — safe for tests
    return WorkersModule.stub()
```

## Observe Worker Lifecycle with Hooks

```python
from lexigram.ai.workers.hooks import (
    WorkerJobCompletedHook,
    WorkerJobStartedHook,
    WorkerMaintenanceRunHook,
)
from lexigram.hooks import HookRegistry


async def on_job_started(hook: WorkerJobStartedHook) -> None:
    print(f"Job started: {hook.job_type}")


async def on_job_completed(hook: WorkerJobCompletedHook) -> None:
    print(f"Job completed: {hook.job_type}")


async def on_maintenance_run(hook: WorkerMaintenanceRunHook) -> None:
    print(f"Maintenance run: {hook.task_type}")


# Register hooks after the app boots
registry = await app.container.resolve(HookRegistry)
registry.register(WorkerJobStartedHook, on_job_started)
registry.register(WorkerJobCompletedHook, on_job_completed)
registry.register(WorkerMaintenanceRunHook, on_maintenance_run)
```

## Bridge Document Ingestion to the RAG Pipeline

```python
from lexigram.ai.workers.adapters import (
    IngestionReport,
    LoaderWorkerBridge,
    RAGIngestionAdapter,
)
from lexigram.ai.workers.document_ingestion.types import Document


# Option A — Bridge ingestion worker as a document loader
from pathlib import Path
from lexigram.logging import get_logger

logger = get_logger(__name__)

bridge = LoaderWorkerBridge(worker=doc_ingestion_worker, timeout=120.0)
registry = loader_registry  # RAG pipeline's LoaderRegistry
registry.register([".pdf", ".docx"], bridge)

# Option B — Full pipeline: ingest → chunk → embed → store
adapter = RAGIngestionAdapter(
    chunker=fixed_size_chunker,
    embedding_worker=batch_worker,
    vector_store=pg_vector_store,
)

documents: list[Document] = [
    Document(content="...", metadata={"document_id": "doc-1"}),
]
result = await adapter.ingest_to_rag(documents, collection="support-docs")
if result.is_ok():
    report: IngestionReport = result.unwrap()
    logger.info("rag_ingestion_complete", chunk_count=report.chunk_count)
```

## Customize Batch Processing with WorkersConfig

```python
from lexigram.ai.workers.config import WorkersConfig
from lexigram.ai.workers.constants import (
    DEFAULT_BASE_BACKOFF,
    DEFAULT_MAX_RETRIES,
)
from lexigram.ai.workers import WorkersModule


config = WorkersConfig(
    enabled=True,
    batch_embedding_concurrency=5,      # Default: 3
    document_ingestion_concurrency=10,   # Default: 3
    enable_maintenance=True,
    dlq_check_interval=120,              # Check DLQ every 2 minutes
)

# Pass to the module
module = WorkersModule.configure(
    config=config,
    enable_scheduler=True,
)

# Or set via environment variables:
# LEX_AI_WORKERS__BATCH_EMBEDDING_CONCURRENCY=5
# LEX_AI_WORKERS__ENABLE_MAINTENANCE=true

# Use constants for retry configuration
max_retries = DEFAULT_MAX_RETRIES      # 5
backoff = DEFAULT_BASE_BACKOFF         # 60 seconds
```

## Disable Workers for a Subprocess

When running a web server that doesn't need background workers:

```yaml
ai_workers:
  enabled: false
```

Or pass `enable_scheduler=False` to `WorkersModule.configure()` to start workers without the scheduler loop.
