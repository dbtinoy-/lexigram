---
title: lexigram-ai-workers Guide
description: Mental model, core concepts, and typical usage of AI background workers
---

## Requirements

| Package | Required | Purpose |
|---------|----------|---------|
| `lexigram` | Yes | Core framework |
| `lexigram-contracts` | Yes | Protocol definitions |
| `lexigram-queue` | Optional | Distributed work queue |
| `lexigram-resilience` | Optional | Retry policies |

AI workloads often involve long-running or batch operations — generating embeddings for thousands of documents, parsing and chunking uploaded files, performing periodic vector store maintenance, or recovering from transient failures. `lexigram-ai-workers` provides a set of **background worker** types that handle these tasks as concurrent, resumable, dependency-injected services.

## Core Concepts

### Worker Types

| Worker | Purpose |
|--------|---------|
| `BatchEmbeddingWorker` | Generate embeddings for batches of text chunks with caching and progress tracking |
| `DocumentIngestionWorker` | Parse, chunk, and store documents into a vector store |
| `MaintenanceWorker` | Periodic tasks: index optimization, cache cleanup, metrics rollup |
| `DeadLetterQueueWorker` | Retry logic with exponential backoff, error classification, failure notifications |

### Lifecycle

Every worker follows a uniform lifecycle:

1. **Registered** in the container by `WorkersProvider` during `register()`.
2. **Resolved and started** as an `asyncio.Task` during `boot()`.
3. **Stopped gracefully** during `shutdown()` via `worker.stop()`.

The `WorkersProvider` wraps each worker's `start()` in a tracked `asyncio.Task` to prevent garbage collection (RUF006).

### Configuration

All workers are governed by `WorkersConfig`, loaded from the `ai_workers:` YAML section or via `LEX_AI_WORKERS__*` environment variables. The `enabled` flag is the master switch — set it to `false` to disable the entire subsystem.

## Typical Usage

### Batch Embedding

```python
from lexigram.ai.workers.batch_embedding import BatchEmbeddingWorker

# Resolve from the container after boot
worker = await container.resolve(BatchEmbeddingWorker)

job_id = await worker.embed_batch(
    chunks=chunks,                   # list[ChunkProtocol]
    collection_name="my-docs",
    model_name="text-embedding-ada-002",
    batch_size=100,
)

# Track progress
progress = await worker.get_progress(job_id)
if progress:
    print(f"{progress.progress_percent:.1f}% done, "
          f"cache hit rate: {progress.cache_hit_rate:.1f}%")
```

### Document Ingestion

```python
from lexigram.ai.workers.document_ingestion import DocumentIngestionWorker

worker = await container.resolve(DocumentIngestionWorker)

job_id = await worker.ingest_document(
    document_id="doc-42",
    file_path="/path/to/report.pdf",
    collection_name="reports",
)
```

### Dead Letter Queue

```python
from lexigram.ai.workers.dlq.worker import DeadLetterQueueWorker

dlq = await container.resolve(DeadLetterQueueWorker)

# Add a failed job
await dlq.add_failed_job(job, error="Rate limit exceeded: retry later")

# Retry manually
await dlq.retry_item(job_id="abc-123")

# Inspect stats
stats = await dlq.get_stats()
print(f"Total failed: {stats.total_items}, "
      f"permanent: {stats.permanent_failures}")
```

### Maintenance Tasks

```python
from lexigram.ai.workers.maintenance.worker import MaintenanceWorker
from lexigram.ai.workers.types import MaintenanceTaskType

maint = await container.resolve(MaintenanceWorker)

maint.register_task(
    name="optimize_indexes",
    task_type=MaintenanceTaskType.INDEX_OPTIMIZATION,
    handler=lambda: vector_store.optimize_indexes(),
    interval_seconds=3600,
)
```

## Common Patterns

### Disable Workers in Tests

```python
module = WorkersModule.stub()  # enable_scheduler=False, no-op workers
```

### Selective Worker Registration

Override `WorkersConfig.enabled: false` and register only the worker you need by resolving it manually:

```python
worker = BatchEmbeddingWorker(
    vector_store=vector_store,
    embedding_provider=embedding_provider,
    queue=queue,
)
await worker.start()
```

### DLQ Notification Handler

```python
async def on_permanent_failure(item: DLQItem) -> None:
    await send_alert(f"Permanent failure: {item.job_id}")

dlq.set_notification_handler(on_permanent_failure)
```

## Best Practices

- ✅ Keep `enable_maintenance: true` in production for automatic DLQ recovery.
- ✅ Use `WorkersModule.stub()` in integration tests to avoid timer interference.
- ✅ Monitor `HealthCheckResult` from each worker — they expose `running` state.
- ❌ Don't run multiple `WorkersProvider` instances for the same worker type.
- ❌ Don't start workers outside the provider lifecycle — let `boot()` handle it.

## Next Steps

- [How-Tos](./HOWTOS.md) — specific task recipes
- [Configuration](./CONFIGURATION.md) — every config key
- [Architecture](./ARCHITECTURE.md) — internal design and extension points
