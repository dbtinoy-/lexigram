# lexigram-ai-workers

AI background workers for the Lexigram Framework — batch embedding, document ingestion, DLQ, maintenance

---

## Overview

AI background workers for the Lexigram Framework. Handles the heavy-lifting off the request path: document ingestion, batch embedding generation, periodic maintenance, and dead-letter-queue recovery — all with progress tracking, exponential backoff, and health reporting. Zero-config usage starts with sensible defaults.


> Full documentation: [docs.lexigram.dev](https://docs.lexigram.dev)
## Install

```bash
uv add lexigram-ai-workers
```

## Quick Start

```python
from lexigram import Application
from lexigram.di.module import Module, module

from lexigram.ai.workers import WorkersModule
from lexigram.ai.workers.config import WorkersConfig

@module(imports=[
    WorkersModule.configure(
        WorkersConfig(
            batch_embedding_concurrency=3,
            document_ingestion_concurrency=3,
            enable_maintenance=True,
            dlq_check_interval=60,
        )
    )
])
class AppModule(Module):
    pass

async with Application.boot(modules=[AppModule]) as app:
    # use app.container to resolve services
    ...
```

## Configuration

> **Zero-config usage:** Call `WorkersModule.configure()` with no arguments to use defaults.

### Option 1 — YAML file

```yaml
# application.yaml
ai_workers:
  enabled: true
  batch_embedding_concurrency: 3
  document_ingestion_concurrency: 3
  enable_maintenance: true
  dlq_check_interval: 60
```

### Option 2 — Profiles + Environment Variables *(recommended)*

```bash
export LEX_AI_WORKERS__BATCH_EMBEDDING_CONCURRENCY=5
# Environment variables for each field
```

### Option 3 — Python

```python
from lexigram.ai.workers.config import WorkersConfig
from lexigram.ai.workers import WorkersModule

config = WorkersConfig(
    enabled=True,
    batch_embedding_concurrency=5,
    document_ingestion_concurrency=3,
    enable_maintenance=True,
    dlq_check_interval=60,
)
WorkersModule.configure(config)
```

### Config reference

| Field | Default | Env var | Description |
|-------|---------|---------|-------------|
| `enabled` | `True` | `LEX_AI_WORKERS__ENABLED` | Master on/off switch for all background workers |
| `batch_embedding_concurrency` | `3` | `LEX_AI_WORKERS__BATCH_EMBEDDING_CONCURRENCY` | Concurrent embedding batch tasks |
| `document_ingestion_concurrency` | `3` | `LEX_AI_WORKERS__DOCUMENT_INGESTION_CONCURRENCY` | Concurrent document processing tasks |
| `enable_maintenance` | `True` | `LEX_AI_WORKERS__ENABLE_MAINTENANCE` | Enable vector-store and cache maintenance |
| `dlq_check_interval` | `60` | `LEX_AI_WORKERS__DLQ_CHECK_INTERVAL` | Seconds between DLQ recovery sweeps |

## Module Factory Methods

| Method | Description |
|--------|-------------|
| `WorkersModule.configure(config, enable_scheduler)` | Configure with explicit config |
| `WorkersModule.stub(config)` | Minimal config for testing |

## Key Features

- **Document ingestion worker**: Parse PDF, DOCX, TXT, HTML, Markdown into chunks for vector store
- **Batch embedding worker**: Process chunks in configurable batches with in-memory embedding cache
- **Dead letter queue worker**: Handle failed jobs with failure classification and exponential backoff
- **Maintenance worker**: Periodic vector store index optimization, cache cleanup, document cleanup
- **Progress tracking**: Job progress monitoring with cache hit rate statistics
- **Adapters**: RAGAdapter, TasksAdapter, LoaderWorker for ecosystem integration

## Testing

```python
async with Application.boot(modules=[WorkersModule.stub()]) as app:
    # your test code
    ...
```

## Key Source Files

| File | What it contains |
|------|-----------------|
| `src/lexigram/ai/workers/module.py` | `WorkersModule.configure()`, `.stub()` |
| `src/lexigram/ai/workers/config.py` | `WorkersConfig` |
| `src/lexigram/ai/workers/document_ingestion/worker.py` | `DocumentIngestionWorker` |
| `src/lexigram/ai/workers/batch_embedding/worker.py` | `BatchEmbeddingWorker` |
| `src/lexigram/ai/workers/dlq/worker.py` | `DeadLetterQueueWorker` |
| `src/lexigram/ai/workers/maintenance/worker.py` | `MaintenanceWorker` |
| `src/lexigram/ai/workers/types.py` | `DLQItem`, `DLQStats`, `MaintenanceTask`, `MaintenanceResult` |
| `src/lexigram/ai/workers/di/provider.py` | `WorkersProvider` |
