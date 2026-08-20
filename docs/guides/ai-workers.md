---
title: "AI Workers"
description: "Background AI work — batch embedding, document ingestion, and maintenance."
---

`lexigram-ai-workers` provides background processing for batch embedding, document ingestion, and scheduled maintenance tasks. Workers register with the task system and run in a separate process or thread pool, leaving the main application loop free for request handling.

For the full configuration reference and advanced features (DLQ recovery, custom schedulers, error classification), see the [`lexigram-ai-workers` package docs](/packages/lexigram-ai-workers/).

---

## 1. Configuration

Add the module and configure the `ai_workers:` section. The module wires ingestion, embedding, DLQ, and maintenance workers:

```python
from lexigram.ai.workers import WorkersModule, WorkersConfig

app.add_module(
    WorkersModule.configure(
        WorkersConfig(
            batch_embedding_concurrency=5,
            document_ingestion_concurrency=4,
            enable_maintenance=True,
            dlq_check_interval=120,
        )
    )
)
```

```yaml title="application.yaml"
ai_workers:
  enabled: true
  batch_embedding_concurrency: 3     # concurrent embedding jobs
  document_ingestion_concurrency: 3  # concurrent document pipelines
  enable_maintenance: true           # vector store + cache cleanup
  dlq_check_interval: 60             # seconds between DLQ recovery sweeps
```

:::tip
Set `dlq_check_interval` higher (300+) in production to avoid unnecessary polling. The DLQ only needs frequent checks during backfill or repair windows.
:::

:::note
`WorkersConfig` is read from the `ai_workers:` block automatically. Pass a config instance directly to `WorkersModule.configure()` for programmatic setup.
:::

---

## 2. Worker Types

Three worker families are registered by `WorkersModule`:

### Batch Embedding

`BatchEmbeddingWorker` processes embedding jobs in parallel. It takes chunk lists, calls the configured embedding provider, and stores results. `embed_batch()` returns a job id you can poll with `get_progress()`:

```python
from lexigram.ai.workers import BatchEmbeddingWorker


class EmbeddingOrchestrator:
    def __init__(self, worker: BatchEmbeddingWorker) -> None:
        self._worker = worker

    async def embed_documents(self, chunks: list, collection_name: str) -> None:
        job_id = await self._worker.embed_batch(
            chunks=chunks,
            collection_name=collection_name,
            model_name="text-embedding-3-small",
        )
        progress = await self._worker.get_progress(job_id)
        print(f"State: {progress.status}, done: {progress.texts_processed}/{progress.total_texts}")
```

### Document Ingestion

`DocumentIngestionWorker` handles parsing, chunking, and storing documents. `ingest_document()` returns a job id; progress is tracked per job:

```python
from pathlib import Path
from lexigram.ai.workers import DocumentIngestionWorker


class DocumentProcessor:
    def __init__(self, worker: DocumentIngestionWorker) -> None:
        self._worker = worker

    async def ingest(self, document_id: str, path: Path) -> None:
        job_id = await self._worker.ingest_document(
            document_id=document_id,
            file_path=path,
            collection_name="knowledge_base",
        )
        progress = await self._worker.get_progress(job_id)
        print(f"Ingestion state: {progress.status}")
```

### Maintenance Worker

`MaintenanceWorker` runs periodic tasks like index optimization, cache cleanup, and health checks. Register tasks with a handler callable, then trigger them manually with `run_task_now()`:

```python
from lexigram.ai.workers import MaintenanceWorker, MaintenanceTaskType


class HealthMonitor:
    def __init__(self, worker: MaintenanceWorker) -> None:
        self._worker = worker

    async def run_checks(self) -> None:
        self._worker.register_task(
            name="vector-optimize",
            task_type=MaintenanceTaskType.INDEX_OPTIMIZATION,
            handler=self._optimize_indexes,
            interval_seconds=3600,
        )
        result = await self._worker.run_task_now("vector-optimize")
        print(f"Optimized {result.items_processed} entries")

    async def _optimize_indexes(self) -> None:
        ...
```

---

## 3. Dead Letter Queue

Failed jobs land in the DLQ for retry, archive, or notification. Configure the sweep interval in `WorkersConfig`:

```python
from lexigram.ai.workers import DeadLetterQueueWorker, FailureCategory


class DLQManager:
    def __init__(self, dlq: DeadLetterQueueWorker) -> None:
        self._dlq = dlq

    async def recover(self) -> None:
        stats = await self._dlq.get_stats()
        if stats.total_items > 0:
            for item in await self._dlq.get_items(category=FailureCategory.TRANSIENT):
                if await self._dlq.retry_item(item["job_id"]):
                    print(f"Retrying job {item['job_id']}")
                else:
                    await self._dlq.archive_item(item["job_id"])
```

Each `DLQItem` tracks failure count, category, backoff, and next retry time. The `calculate_backoff()` method uses exponential backoff capped at 3600 seconds.

---

## 4. Testing

Use `WorkersModule.stub()` for unit tests. It disables the background scheduler and uses no-op worker implementations:

```python
from lexigram import Application
from lexigram.ai.workers import WorkersModule
from lexigram.contracts.infra.tasks.protocols import TaskWorkerProtocol


async def test_worker_registration() -> None:
    async with Application.boot(modules=[WorkersModule.stub()]) as app:
        worker = await app.container.resolve(TaskWorkerProtocol)
        assert worker is not None
```

You can also bind hand-rolled fakes to `TaskWorkerProtocol` in any container — the rest of your code depends only on the protocol.

---

## Next Steps

- [Dependency Injection](/fundamentals/dependency-injection/) — binding workers to protocols
- [Tasks & Scheduling](/guides/background-jobs/) — registering workers with the task system
- [Testing](/guides/testing/) — substituting stubs for infrastructure
- [`lexigram-ai-workers` package](/packages/lexigram-ai-workers/) — full config reference, DLQ recovery, error classifier
