---
title: lexigram-ai-workers Troubleshooting
description: Common errors, causes, and fixes
---

## WorkerError: Worker not starting

**Error:** Log shows `worker_resolve_failed` for a worker type.

**Cause:** The worker's constructor dependencies are not registered in the DI container.

**Fix:** Ensure that `VectorStoreProtocol`, `TaskQueueProtocol`, and `EmbeddingProvider` implementations are registered before the worker provider boots.

```python
container.singleton(VectorStoreProtocol, PgVectorStore(config=...))
container.singleton(TaskQueueProtocol, RedisTaskQueue(url=...))
```

## RuntimeError: Failed to enqueue embedding job

**Error:** `RuntimeError: Failed to enqueue embedding job: ...`

**Cause:** The `TaskQueueProtocol.enqueue()` returned `Err(...)`.

**Fix:** Check that the task queue backend (Redis, RabbitMQ, Postgres) is running and reachable.

```python
result = await queue.enqueue(job_data)
if result.is_err():
    logger.error("enqueue_failed", error=str(result.unwrap_err()))
```

## MaintenanceTask never runs

**Cause:** Either `enable_maintenance: false` in config, or the task was registered without a schedule.

**Fix:** Verify config and ensure each task has `interval_seconds` or `schedule_cron`.

```python
maint.register_task(
    name="cleanup",
    task_type=MaintenanceTaskType.CACHE_CLEANUP,
    handler=cleanup_fn,
    interval_seconds=3600,  # Required
)
```

## DeadLetterQueue stops processing

**Error:** No retries happening for items in DLQ.

**Cause 1:** `dlq_check_interval` is too high (default 60s). Retry check is a background loop.

**Cause 2:** Items have `failure_category == PERMANENT` — these are never retried.

**Cause 3:** `retry_count >= max_retries` (default 5).

**Fix:** Check `DLQItem.can_retry()` to understand why an item is skipped.

```python
item = dlq._items.get("job-id")
if item:
    print(f"Can retry: {item.can_retry()}, retries: {item.retry_count}/{item.max_retries}")
```

## BatchEmbeddingProgress shows 0% forever

**Cause:** The `BatchEmbeddingWorker` could not resolve a `TaskWorkerProtocol` from the container, so `_handle_batch_embed` never executes.

**Fix:** Register a `TaskWorkerProtocol` implementation before booting the workers provider.

```python
container.singleton(TaskWorkerProtocol, RedisTaskWorker)
```

## Document ingestion fails silently

**Cause:** The `DocumentParser` (default `UniversalDocumentParser`) cannot parse the file format.

**Fix:** Pass a custom parser that handles the file format.

```python
from lexigram.ai.workers.document_ingestion.parser import DocumentParser


class PDFParser(DocumentParser):
    async def parse(self, path: Path) -> list[ChunkProtocol]:
        ...


worker = DocumentIngestionWorker(
    vector_store=store,
    queue=queue,
    document_parser=PDFParser(),
)
```

## Debug Tips

- Set `LOG_LEVEL=DEBUG` to see worker lifecycle events.
- Check `worker.health_check()` for running state.
- Use `worker.get_stats()` to inspect progress and history.
- Run `WorkersModule.stub()` in tests to avoid background task interference.
