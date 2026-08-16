---
title: lexigram-vector Quickstart
description: Install, configure, and run your first vector store in under 5 minutes.
sidebar:
  order: 1
---

```bash
uv add lexigram-vector
```

Install the backend driver for your vector store:

```bash
uv add "lexigram-vector[pgvector]"    # PostgreSQL + pgvector
uv add "lexigram-vector[qdrant]"      # Qdrant
uv add "lexigram-vector[pinecone]"    # Pinecone
uv add "lexigram-vector[chroma]"      # ChromaDB
uv add "lexigram-vector[weaviate]"    # Weaviate
uv add "lexigram-vector[all]"         # Every backend
```

---

## Minimal Example

```python
import asyncio
from lexigram import Application
from lexigram.vector import VectorModule


async def main() -> None:
    async with Application.boot(
        name="vector-demo",
        modules=[VectorModule.configure()],
    ) as app:
        store = await app.container.resolve(VectorStoreProtocol)
        await store.create_collection(
            CollectionConfig(name="my_docs", dimension=1536)
        )
        print("Collection ready!")


asyncio.run(main())
```

---

## What Just Happened

1. `VectorModule.configure()` created a `VectorProvider` with default config (in-memory backend).
2. The provider registered `VectorStoreProtocol` and `VectorCollectionProtocol` in the container.
3. An in-memory `MemoryVectorStore` was created and connected during `boot()`.
4. `store.create_collection()` created a vector collection capable of storing 1536-dimensional embeddings.

---

## Next Steps

- [Guide](./GUIDE.md) — mental model, core concepts, common patterns
- [Configuration](./CONFIGURATION.md) — all config keys and env vars
- [How-Tos](./HOWTOS.md) — copy-pasteable recipes
