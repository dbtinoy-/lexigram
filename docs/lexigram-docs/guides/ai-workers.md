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

`BatchEmbeddingWorker` processes embedding jobs in parallel. It accepts `BatchEmbeddingJob` items, calls the configured embedding provider, and stores results:

```python
from lexigram.ai.workers import BatchEmbeddingWorker, BatchEmbeddingJob
from lexigram.result import Result


class EmbeddingOrchestrator:
    def __init__(self, worker: BatchEmbeddingWorker) -> None:
        self._worker = worker

    async def embed_documents(
        self, texts: list[str],
    ) -> Result[list[str], str]:
        job = BatchEmbeddingJob(texts=texts)
        return await self._worker.execute(job)
```

### Document Ingestion

`DocumentIngestionWorker` handles parsing, chunking, and storing documents. It tracks progress with `IngestionProgress` and returns `IngestionResult`:

```python
from lexigram.ai.workers import DocumentIngestionWorker, DocumentIngestionJob


class DocumentProcessor:
    def __init__(self, worker: DocumentIngestionWorker) -> None:
        self._worker = worker

    async def ingest(self, path: str) -> None:
        job = DocumentIngestionJob(source=path)
        result = await self._worker.execute(job)
        if result.is_ok():
            print(f"Ingested {result.unwrap().chunks_created} chunks")
```

### Maintenance Worker

`MaintenanceWorker` runs periodic tasks like index optimization, cache cleanup, and health checks:

```python
from lexigram.ai.workers import MaintenanceWorker, MaintenanceTask, MaintenanceTaskType


class HealthMonitor:
    def __init__(self, worker: MaintenanceWorker) -> None:
        self._worker = worker

    async def run_checks(self) -> None:
        task = MaintenanceTask(
            name="vector-optimize",
            task_type=MaintenanceTaskType.INDEX_OPTIMIZATION,
            interval_seconds=3600,
        )
        result = await self._worker.run(task)
        if result.is_ok():
            print(f"Optimized {result.unwrap().items_processed} entries")
```

---

## 3. Dead Letter Queue

Failed jobs land in the DLQ for retry, archive, or notification. Configure the sweep interval in `WorkersConfig`:

```python
from lexigram.ai.workers import DeadLetterQueueWorker, DLQItem, DLQStats
from lexigram.ai.workers import DLQAction, FailureCategory


class DLQManager:
    def __init__(self, dlq: DeadLetterQueueWorker) -> None:
        self._dlq = dlq

    async def recover(self) -> None:
        stats: DLQStats = await self._dlq.get_stats()
        if stats.total_items > 0:
            for item in stats.by_category:
                action = await self._dlq.process(
                    DLQItem(
                        job_id="...",
                        failure_category=FailureCategory.TRANSIENT,
                    )
                )
                if action == DLQAction.RETRY:
                    print(f"Retrying job")
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
