---
title: lexigram-vector Guide
description: Vector store backends (pgvector, Qdrant, Pinecone, Chroma, in-memory) for embeddings.
sidebar:
  order: 2
---

## Requirements

| Package | Required | Purpose |
|---------|----------|---------|
| `lexigram` | Yes | Core framework |
| `lexigram-contracts` | Yes | Protocol definitions |
| `pgvector` | Recommended | PostgreSQL vector backend (via asyncpg) |
| `qdrant-client` | Optional | Qdrant vector backend |
| `pinecone` | Optional | Pinecone vector backend |
| `weaviate-client` | Optional | Weaviate vector backend |

`lexigram-vector` provides async vector store backends for similarity search over embeddings. It is the persistence layer for AI workloads — RAG retrieval, semantic memory, agent context, and embedding-based search.

## The Problem

Applications that use embeddings (from LLMs, image models, or custom encoders) need a place to store and search them efficiently. Different deployment scenarios demand different backends — pgvector for Postgres-native setups, Qdrant/Pinecone for dedicated vector databases, Chroma for local development, and in-memory for tests.

## Mental Model

`lexigram-vector` abstracts over backends with two core protocols:

```
VectorStoreProtocol        → collection lifecycle (create, delete, list, connect)
    └── VectorCollectionProtocol  → vector operations (upsert, search, get, delete)
```

A `VectorStore` manages connections and collections. Each collection holds vectors of a fixed dimension with a distance metric. Operations are async end-to-end.

---

## Core Concepts

### VectorStoreProtocol

Top-level lifecycle and collection management. Implementations: `MemoryVectorStore`, `PgVectorStore`, `QdrantStore`, `PineconeStore`, `ChromaStore`, `WeaviateStore`.

```python
from lexigram.contracts.data.vector.protocols import VectorStoreProtocol

store = await container.resolve(VectorStoreProtocol)
await store.connect()
await store.create_collection(CollectionConfig(name="docs", dimension=1536))
```

### VectorCollectionProtocol

Per-collection vector operations:

```python
collection = await store.get_collection("docs")

# Upsert vectors
result = await collection.upsert([
    VectorRecord(id="1", vector=[0.1, 0.2, ...], metadata={"source": "doc1"}),
])

# Similarity search
results = await collection.search(
    SearchQuery(vector=[0.1, 0.2, ...], top_k=5)
)

# Retrieve by ID
records = await collection.get(["1", "2"])

# Delete
delete_result = await collection.delete(["1"])
```

### Exception Hierarchy

All vector exceptions extend `VectorError(InfrastructureError)`:

| Exception | When |
|-----------|------|
| `VectorConnectionError` | Failed to connect to backend |
| `VectorConfigError` | Invalid configuration |
| `CollectionNotFoundError` | Collection doesn't exist |
| `CollectionAlreadyExistsError` | Already exists on create |
| `DimensionMismatchError` | Vector dimension mismatch |
| `FilterCompilationError` | Couldn't compile metadata filter |
| `VectorUpsertError` | Upsert failed |
| `VectorSearchError` | Search failed |
| `VectorDeleteError` | Delete failed |
| `VectorTimeoutError` | Operation timed out |

### Multi-Backend Mode

`VectorConfig.backends` allows multiple named backends:

```yaml
vector:
  backends:
    - name: primary
      primary: true
      backend: qdrant
      qdrant:
        url: http://qdrant:6333
    - name: archive
      backend: pgvector
      pgvector:
        database: archive_db
```

Each backend is resolvable via `Annotated[VectorStoreProtocol, Named("archive")]`. The primary backend also receives the unnamed binding.

---

## Typical Usage

### Configure and Use pgvector

```python
import asyncio
from lexigram import Application
from lexigram.vector import VectorModule, VectorConfig
from lexigram.contracts.data.vector.types import (
    CollectionConfig,
    SearchQuery,
    VectorRecord,
)


async def main() -> None:
    config = VectorConfig(
        backend="pgvector",
        pgvector__database="primary",
        default_dimension=1536,
    )

    async with Application.boot(
        name="vector-app",
        modules=[VectorModule.configure(config)],
    ) as app:
        store = await app.container.resolve(VectorStoreProtocol)
        await store.create_collection(
            CollectionConfig(name="embeddings", dimension=1536)
        )
        collection = await store.get_collection("embeddings")

        result = await collection.upsert([
            VectorRecord(
                id="vec-1",
                vector=[0.1] * 1536,
                metadata={"text": "hello world"},
            ),
        ])
        print(f"Upserted: {result.upserted_count}")

        results = await collection.search(
            SearchQuery(vector=[0.1] * 1536, top_k=5)
        )
        for r in results:
            print(f"Score: {r.score:.4f}, ID: {r.id}")


asyncio.run(main())
```

---

## Integration

`lexigram-vector` exports `VectorStoreProtocol` and `VectorCollectionProtocol` from `lexigram.contracts.data.vector.protocols`. Other packages consume these contracts via DI:

| Protocol | Used by | Resolved from |
|----------|---------|---------------|
| `VectorStoreProtocol` | RAG pipelines, memory, agents | `VectorProvider` |
| `VectorCollectionProtocol` | Ad-hoc per-collection ops | Via `store.get_collection()` |

The `DocumentVectorStoreAdapter` bridges the infra-level `VectorStoreProtocol` with the AI-layer `DocumentProtocol`, adding embedding generation and document-level types.

---

## Best Practices

- ✅ Use `MemoryVectorStore` for tests — it requires no external service.
- ✅ Use `stub()` module for isolated test setups without infrastructure.
- ✅ Configure `upsert_batch_size` to balance throughput and memory.
- ✅ Set `max_retries` and `retry_delay` for transient network failures.
- ✅ Use `vector.validate_for_environment(env)` to catch production misconfigs.
- ❌ Don't use `MemoryVectorStore` or `ChromaStore` in production (they're development-only).
- ❌ Don't forget to match `default_dimension` to your embedding model's output.
- ❌ Don't call `collection.search()` with a vector of wrong dimensionality.

---

## Next Steps

- [Architecture](./ARCHITECTURE.md) — provider lifecycle, contracts, backend system
- [Configuration](./CONFIGURATION.md) — all config keys
- [How-Tos](./HOWTOS.md) — multi-backend, embedding client, reranking
- [Troubleshooting](./TROUBLESHOOTING.md) — common errors
