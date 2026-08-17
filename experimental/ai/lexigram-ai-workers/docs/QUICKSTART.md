---
title: lexigram-ai-workers Quickstart
description: Get AI background workers running in under 5 minutes
---

:::note[Maturity]
Alpha (0.1.x) — MIT. Public APIs may change before 1.0.
:::

## Install

```bash
uv add lexigram-ai-workers
```

`lexigram-ai-workers` depends on `lexigram` and `lexigram-contracts` (installed automatically).

## Minimal Workers Setup

```python
import asyncio

from lexigram import Application, LexigramConfig
from lexigram.ai.workers import WorkersModule


async def main() -> None:
    config = LexigramConfig.from_yaml("application.yaml")
    app = Application(name="my-app", config=config)
    app.add_module(WorkersModule.configure())
    await app.start()

    print("Worker subsystem is running")
    await asyncio.sleep(10)

    await app.stop()


asyncio.run(main())
```

With `application.yaml`:

```yaml
ai_workers:
  enabled: true
  batch_embedding_concurrency: 3
  document_ingestion_concurrency: 3
```

## What Just Happened

1. `WorkersModule.configure()` creates a `DynamicModule` with a `WorkersProvider`.
2. `Application.boot()` starts the provider lifecycle:
   - **register** — `WorkersConfig` and worker types are bound in the container.
   - **boot** — workers (`BatchEmbeddingWorker`, `DocumentIngestionWorker`, `MaintenanceWorker`, `DeadLetterQueueWorker`) are resolved and started as background tasks.

## Next Steps

- [Guide](./GUIDE.md) — mental model, worker types, typical workflows
- [How-Tos](./HOWTOS.md) — task-oriented recipes
- [Configuration](./CONFIGURATION.md) — all config keys and env-var overrides
