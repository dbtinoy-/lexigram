---
title: lexigram-ai-memory Quickstart
description: Install, configure, and start using AI memory in under 5 minutes.
---

AI memory system — episodic, semantic, and working memory with pluggable backends and consolidation.

:::note[Maturity]
Alpha (0.1.x) — public APIs may change before 1.0.
:::

## Install

```bash
uv add lexigram-ai-memory
```

## Minimal Usage

```python
import asyncio
from datetime import UTC, datetime

from lexigram import Application
from lexigram.ai.memory import MemoryModule, MemoryConfig
from lexigram.contracts.ai.memory import MemoryEntry, MemoryQuery


async def main():
    config = MemoryConfig()
    async with Application.boot(
        name="memory-demo",
        modules=[MemoryModule.configure(config)],
    ) as app:
        store = await app.container.resolve(MemoryStoreProtocol)

        entry = MemoryEntry(
            id="1",
            content="The capital of France is Paris.",
            role="assistant",
            timestamp=datetime.now(UTC),
            importance=0.9,
        )
        await store.store(entry)

        results = await store.retrieve(
            MemoryQuery(query="france capital", top_k=5)
        )
        for r in results:
            print(f"[{r.score:.2f}] {r.entry.content}")


asyncio.run(main())
```

## What Just Happened

1. **`MemoryModule.configure(config)`** wired `MemoryProvider` into the container.
2. **`MemoryStoreProtocol`** resolved the default `InMemoryMemoryBackend`.
3. **`store.store()`** saved an entry with importance metadata.
4. **`store.retrieve()`** searched entries by query and returned scored results.

## Next Steps

- [Guide](./GUIDE.md) — three memory tiers, consolidation, end-to-end usage
- [How-Tos](./HOWTOS.md) — common memory patterns
- [Configuration](./CONFIGURATION.md) — all config keys
