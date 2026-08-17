---
title: lexigram-ai-workers Configuration
description: Every config key, type, default, and env-var override
---

Loaded from the `ai_workers:` section of `application.yaml`. Environment variable prefix: `LEX_AI_WORKERS__`.

## WorkersConfig

```yaml
ai_workers:
  enabled: true
  batch_embedding_concurrency: 3
  document_ingestion_concurrency: 3
  enable_maintenance: true
  dlq_check_interval: 60
```

### Keys

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `enabled` | `bool` | `true` | `LEX_AI_WORKERS__ENABLED` | Master on/off switch for all background workers |
| `batch_embedding_concurrency` | `int` | `3` | `LEX_AI_WORKERS__BATCH_EMBEDDING_CONCURRENCY` | Concurrency level for batch embedding execution |
| `document_ingestion_concurrency` | `int` | `3` | `LEX_AI_WORKERS__DOCUMENT_INGESTION_CONCURRENCY` | Concurrency level for document parsing and chunking |
| `enable_maintenance` | `bool` | `true` | `LEX_AI_WORKERS__ENABLE_MAINTENANCE` | Enable vector store and cache maintenance tasks |
| `dlq_check_interval` | `int` | `60` | `LEX_AI_WORKERS__DLQ_CHECK_INTERVAL` | Interval in seconds for DLQ recovery sweeps |

## Env-var Override Example

```bash
LEX_AI_WORKERS__ENABLED=true \
LEX_AI_WORKERS__BATCH_EMBEDDING_CONCURRENCY=5 \
LEX_AI_WORKERS__DLQ_CHECK_INTERVAL=120 \
  python -m my_app
```

## Minimal Production Config

```yaml
ai_workers:
  enabled: true
  batch_embedding_concurrency: 5
  document_ingestion_concurrency: 5
  enable_maintenance: true
  dlq_check_interval: 120
```
