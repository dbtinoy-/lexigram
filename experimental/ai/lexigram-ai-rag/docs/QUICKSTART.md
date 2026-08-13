---
title: lexigram-ai-rag Quickstart
description: Install, configure, and run your first RAG pipeline in under 5 minutes.
sidebar:
  order: 1
---

```bash
uv add lexigram-ai-rag
```

Optional extras for PDF loading, web scraping, reranking, and compression:

```bash
uv add "lexigram-ai-rag[pdf,web,compression,reranking]"
```

---

## Minimal Example

```python
import asyncio
from lexigram import Application
from lexigram.ai.rag import RAGModule


async def main() -> None:
    async with Application.boot(
        name="rag-demo",
        modules=[RAGModule.configure()],
    ) as app:
        pipeline = await app.container.resolve(RAGPipelineProtocol)
        result = await pipeline.execute(
            RAGContext(query="What is Lexigram?")
        )
        if result.is_ok():
            print(result.unwrap().answer)


asyncio.run(main())
```

---

## What Just Happened

1. `RAGModule.configure()` created a `RAGProvider` with default config (in-memory backing, `top_k=5`, chunking enabled).
2. The provider registered `RAGPipelineProtocol` and `RetrievalStrategyProtocol` in the container.
3. `pipeline.execute()` ran retrieval → synthesis → quality assurance and returned a `RAGResponse`.

---

## Next Steps

- [Guide](./GUIDE.md) — mental model, core concepts, common patterns
- [Configuration](./CONFIGURATION.md) — all config keys and env vars
- [How-Tos](./HOWTOS.md) — copy-pasteable recipes
