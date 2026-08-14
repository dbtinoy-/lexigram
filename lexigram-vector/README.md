# lexigram-vector

Vector storage infrastructure for the Lexigram Framework with Qdrant, ChromaDB,
PGVector, Pinecone, and in-memory backends. Provides embedding clients, vector
search, hybrid retrieval, reranking, and Named DI multi-store support.

---

## Overview

Vector storage infrastructure for the Lexigram Framework with Qdrant, ChromaDB, PGVector, Pinecone, and in-memory backends. Provides embedding clients, vector search, hybrid retrieval, reranking, and Named DI multi-store support.

**Architecture note**: This package provides infrastructure and data-layer
functionality for vector storage and retrieval. While it is commonly used by AI
and RAG features (`lexigram-ai-rag`), it is a general-purpose vector database
abstraction suitable for any use case requiring semantic search, similarity
matching, or high-dimensional data storage.

> Full documentation: [docs.lexigram.dev](https://docs.lexigram.dev)
>
> Deep-dive guide: [Vector Stores in lexigram-vector](docs/vector-stores.md)

## Install

```bash
uv add lexigram lexigram-vector

# With Qdrant support
uv add "lexigram-vector[qdrant]"

# With ChromaDB support
uv add "lexigram-vector[chroma]"

# With PGVector support (requires lexigram-sql for database access)
uv add "lexigram-vector[pgvector]"

# With Pinecone support
uv add "lexigram-vector[pinecone]"

# With embedding support
uv add openai  # or anthropic, cohere, etc.
```

## Quick Start

```python
import asyncio

from lexigram import Application
from lexigram.contracts.data.vector import (
    CollectionConfig,
    SearchQuery,
    VectorRecord,
    VectorStoreProtocol,
)
from lexigram.vector import VectorModule


async def main() -> None:
    async with Application.boot(modules=[VectorModule.stub()]) as app:
        store = await app.container.resolve(VectorStoreProtocol)

        # Create a collection
        await store.create_collection(
            CollectionConfig(name="documents", dimension=1536)
        )

        # Upsert vectors through the collection handle
        collection = await store.get_collection("documents")
        await collection.upsert(
            [
                VectorRecord(
                    id="doc1",
                    vector=[0.1] * 1536,
                    metadata={"title": "Document 1", "category": "tech"},
                ),
                VectorRecord(
                    id="doc2",
                    vector=[0.2] * 1536,
                    metadata={"title": "Document 2", "category": "science"},
                ),
            ]
        )

        # Search
        results = await collection.search(SearchQuery(vector=[0.15] * 1536, top_k=5))

        for result in results:
            print(f"{result.id}: {result.metadata['title']} (score: {result.score})")


if __name__ == "__main__":
    asyncio.run(main())
```

## Configuration

> **Zero-config usage:** Call `VectorModule.configure()` with no arguments to start
> with all built-in defaults — no config file or environment variables needed.
> See the [Config reference](#config-reference) below for all default values.

### Option 1 — YAML file *(use when config lives in a single explicit file)*

Declare config in a YAML file loaded at a fixed, explicit path.  `LEX_*`
environment variables override YAML values at startup.

`config_section = "vector"` is already set on this class — `section=` can be
omitted in all calls.  Pass an explicit `section=` only to override the
default (e.g. when this config is nested under a non-standard key).

```yaml
# application.yaml — copy example.yaml for a fully-annotated starting point
vector:
  backend: "qdrant"             # memory, pgvector, pinecone, qdrant, chroma
  default_dimension: 1536       # 1536 = OpenAI text-embedding-3-small
  upsert_batch_size: 100
  qdrant:
    url: "http://localhost:6333"
    api_key: null               # LEX_VECTOR__QDRANT__API_KEY
```
Then load and wire it in your composition root:

```python
from lexigram.vector.config import VectorConfig
from lexigram.vector import VectorModule

config = VectorConfig.from_yaml("application.yaml")
app.add_module(VectorModule.configure(config))
```

Environment variables override YAML values and use the `LEX_VECTOR__` prefix:

```bash
LEX_VECTOR__BACKEND=qdrant
```

### Option 2 — Profiles + Environment Variables *(recommended for production, staging, Docker, CI/CD)*

Loads a base `application.yaml`, then overlays an environment-specific
file (`application.production.yaml`, `application.staging.yaml`, etc.)
based on the `LEX_PROFILE` environment variable.  `LEX_*` env vars are
applied last as the final override layer.

```bash
# Set LEX_VECTOR__* env vars before starting the process
export LEX_VECTOR__ENABLED=true
```

```python
from lexigram.vector.config import VectorConfig
from lexigram.vector import VectorModule

config = VectorConfig.from_env_profile()
app.add_module(VectorModule.configure(config))
```

> **Loading order:** `application.yaml` (base) →
> `application.{profile}.yaml` (overlay, if `LEX_PROFILE` is set) →
> `LEX_*` environment variables (final override).  Missing files are
> silently skipped so this is safe to call in all environments.

### Option 3 — Python *(use when config is dynamic or computed at boot)*

Build config in code at boot time. Use this when settings are **derived at
runtime** — e.g. secrets fetched from a vault, per-tenant configurations,
or when you need multiple module instances with different settings.

```python
from lexigram.vector import VectorModule
from lexigram.vector.config import QdrantConfig, VectorConfig

app.add_module(
    VectorModule.configure(
        VectorConfig(
            backend="qdrant",
            qdrant=QdrantConfig(
                url="http://localhost:6333",
            ),
        )
    )
)
```

### Config reference

#### VectorConfig

Top-level configuration loaded from `application.yaml`'s `vector:` key or from
`LEX_VECTOR__*` environment variables.

| Field | Default | Env var | Description |
|-------|---------|---------|-------------|
| `enabled` | `True` | `LEX_VECTOR__ENABLED` | Enable the vector store subsystem |
| `backend` | `"memory"` | `LEX_VECTOR__BACKEND` | Vector store backend (`"memory"`, `"qdrant"`, `"chroma"`, `"pgvector"`, `"pinecone"`) |
| `default_distance_metric` | `DistanceMetric.COSINE` | `LEX_VECTOR__DEFAULT_DISTANCE_METRIC` | Default distance metric for new collections |
| `default_index_type` | `IndexType.HNSW` | `LEX_VECTOR__DEFAULT_INDEX_TYPE` | Default index type for new collections |
| `default_dimension` | `1536` | `LEX_VECTOR__DEFAULT_DIMENSION` | Default vector dimension (matches OpenAI text-embedding-ada-002) |
| `upsert_batch_size` | `100` | `LEX_VECTOR__UPSERT_BATCH_SIZE` | Number of vectors per upsert batch |
| `max_retries` | `3` | `LEX_VECTOR__MAX_RETRIES` | Maximum number of retries for operations |
| `retry_delay` | `0.5` | `LEX_VECTOR__RETRY_DELAY` | Delay between retries in seconds |
| `pgvector` | `PgVectorConfig()` | — | PGVector-specific settings |
| `pinecone` | `PineconeConfig()` | — | Pinecone-specific settings |
| `qdrant` | `QdrantConfig()` | — | Qdrant-specific settings |
| `weaviate` | `WeaviateConfig()` | — | Weaviate-specific settings |
| `memory` | `MemoryConfig()` | — | In-memory-specific settings |
| `backends` | `[]` | — | List of `NamedVectorConfig` entries for multi-store support |
| `tenancy` | `VectorTenancyConfig()` | — | Per-tenant collection isolation (`VectorTenancyConfig`) |
| `collection_name` | `"default"` | `LEX_VECTOR__COLLECTION_NAME` | Default collection name for AI-layer operations |
| `enable_cache` | `False` | `LEX_VECTOR__ENABLE_CACHE` | Enable embedding caching (requires a `CacheBackend` binding) |
| `cache_ttl` | `86400` | `LEX_VECTOR__CACHE_TTL` | Embedding cache TTL in seconds (default: 24 hours) |

When `backends` is non-empty, each entry is registered under
`Annotated[VectorStoreProtocol, Named(entry.name)]`. The first entry (or the
one with `primary=True`) also receives the unnamed `VectorStoreProtocol`
binding for backward compatibility.

#### Backend-Specific Configuration

##### QdrantConfig

| Field | Default | Env var | Description |
|-------|---------|---------|-------------|
| `url` | `"http://localhost:6333"` | `LEX_VECTOR__QDRANT__URL` | Qdrant server URL |
| `api_key` | `None` | `LEX_VECTOR__QDRANT__API_KEY` | Qdrant API key (optional) |
| `grpc_port` | `6334` | `LEX_VECTOR__QDRANT__GRPC_PORT` | gRPC port for Qdrant |
| `prefer_grpc` | `True` | `LEX_VECTOR__QDRANT__PREFER_GRPC` | Whether to prefer gRPC over HTTP |
| `timeout` | `30.0` | `LEX_VECTOR__QDRANT__TIMEOUT` | Request timeout in seconds |

##### PgVectorConfig

| Field | Default | Env var | Description |
|-------|---------|---------|-------------|
| `database` | `"primary"` | `LEX_VECTOR__PGVECTOR__DATABASE` | Name of the database backend from `db.backends` to use |
| `schema` | `"public"` | `LEX_VECTOR__PGVECTOR__SCHEMA` | Database schema for vector tables |
| `default_lists` | `100` | `LEX_VECTOR__PGVECTOR__DEFAULT_LISTS` | Default number of lists for IVFFlat index |
| `default_probes` | `10` | `LEX_VECTOR__PGVECTOR__DEFAULT_PROBES` | Default number of probes for IVFFlat index |
| `default_ef_search` | `64` | `LEX_VECTOR__PGVECTOR__DEFAULT_EF_SEARCH` | Default ef_search for HNSW index |
| `table_prefix` | `"vec_"` | `LEX_VECTOR__PGVECTOR__TABLE_PREFIX` | Prefix for vector storage tables |
| `create_extension` | `True` | `LEX_VECTOR__PGVECTOR__CREATE_EXTENSION` | Whether to create pgvector extension if missing |

**Note**: PGVector requires `lexigram-sql` and a configured `DatabaseProviderProtocol`.
The `database` field refers to a named database backend from `db.backends`.

##### PineconeConfig

| Field | Default | Env var | Description |
|-------|---------|---------|-------------|
| `api_key` | `""` | `LEX_VECTOR__PINECONE__API_KEY` | Pinecone API key (required) |
| `environment` | `""` | `LEX_VECTOR__PINECONE__ENVIRONMENT` | Pinecone environment (e.g., `"us-west1-gcp"`) |
| `index_name` | `""` | `LEX_VECTOR__PINECONE__INDEX_NAME` | Name of the Pinecone index |
| `namespace` | `""` | `LEX_VECTOR__PINECONE__NAMESPACE` | Default namespace for the index |
| `timeout` | `30.0` | `LEX_VECTOR__PINECONE__TIMEOUT` | Request timeout in seconds |
| `pool_threads` | `4` | `LEX_VECTOR__PINECONE__POOL_THREADS` | Number of threads for the connection pool |

##### MemoryConfig

| Field | Default | Env var | Description |
|-------|---------|---------|-------------|
| `max_collections` | `100` | `LEX_VECTOR__MEMORY__MAX_COLLECTIONS` | Maximum number of collections in memory |
| `max_vectors_per_collection` | `100,000` | `LEX_VECTOR__MEMORY__MAX_VECTORS_PER_COLLECTION` | Maximum number of vectors per collection |

#### NamedVectorConfig

Configuration for a single named vector store backend (used in multi-store setups):

| Field | Description |
|-------|-------------|
| `name` | Unique backend identifier (used as the `Named()` DI key) |
| `primary` | Whether this backend also receives the unnamed `VectorStoreProtocol` binding |
| `backend` | Vector store driver for this named backend |
| `pgvector` | `PgVectorConfig` for this backend |
| `pinecone` | `PineconeConfig` for this backend |
| `qdrant` | `QdrantConfig` for this backend |
| `memory` | `MemoryConfig` for this backend |

**Example multi-store setup**:

```python
from lexigram.vector.config import (
    NamedVectorConfig,
    PgVectorConfig,
    QdrantConfig,
    VectorConfig,
)

VectorModule.configure(
    VectorConfig(
        backends=[
            NamedVectorConfig(
                name="primary",
                primary=True,
                backend="qdrant",
                qdrant=QdrantConfig(
                    url="http://qdrant-primary:6333",
                ),
            ),
            NamedVectorConfig(
                name="rag",
                backend="pgvector",
                pgvector=PgVectorConfig(
                    database="rag",
                    schema="vectors",
                ),
            ),
        ]
    )
)
```

Inject named stores:

```python
from typing import Annotated
from lexigram.contracts.data.vector.protocols import VectorStoreProtocol
from lexigram.di.markers import Named


class MyService:
    def __init__(
        self,
        store: VectorStoreProtocol,  # primary
        rag: Annotated[VectorStoreProtocol, Named("rag")],
    ) -> None:
        self.store = store
        self.rag = rag
```

## Module Factory Methods

| Method | Description |
|--------|-------------|
| `VectorModule.configure(config=None, enable_reranking=False)` | Vector store with explicit `VectorConfig`; registers `VectorStoreProtocol` and `VectorCollectionProtocol`. `enable_reranking` enables cross-encoder reranking of retrieval results |
| `VectorModule.stub(config=None)` | In-memory backend with no external service dependencies, for tests |

## Key Features

- **Multi-backend vector storage** — Qdrant, ChromaDB, PGVector, Pinecone, and in-memory backends
- **Embedding client** — OpenAI-compatible async client for generating embeddings (`OpenAICompatibleEmbeddingClient`)
- **Embedding cache** — In-memory and persistent caching to reduce embedding API calls (`EmbeddingCache`, `InMemoryEmbeddingCache`)
- **Vector search** — Similarity search with metadata filtering and distance metrics
- **Hybrid retrieval** — BM25 + vector search with reciprocal rank fusion (`HybridRetriever`, `BM25Retriever`, `RRFReranker`)
- **Reranking** — Cross-encoder reranking, diversity reranking, and similarity reranking for improved relevance (`CrossEncoderReranker`, `DiversityReranker`, `RerankerPipeline`)
- **Metadata filtering** — Structured filtering on metadata fields with backend-specific filter compilers
- **Named DI multi-store** — Multiple vector stores registered as `Annotated[VectorStoreProtocol, Named("rag")]`
- **Collection management** — Create, delete, list collections with automatic schema inference
- **Batch operations** — Efficient batch upsert, delete, and search with configurable batch sizes
- **Distance metrics** — Cosine, Euclidean, and dot product similarity metrics
- **Index types** — HNSW, IVFFlat, and backend-specific index configuration

## Testing

```python
async with Application.boot(modules=[VectorModule.stub()]) as app:
    store = await app.container.resolve(VectorStoreProtocol)
    # Test with the in-memory backend
    ...
```

## Key Source Files

| File | What it contains |
|------|-----------------|
| `src/lexigram/vector/module.py` | `VectorModule.configure()` and `.stub()` |
| `src/lexigram/vector/config.py` | `VectorConfig`, `VectorTenancyConfig`, `NamedVectorConfig`, backend configs |
| `src/lexigram/vector/di/provider.py` | `VectorProvider` boot and registration |
| `src/lexigram/vector/di/factories.py` | Factory functions for creating vector stores |
| `src/lexigram/vector/backends/qdrant/` | Qdrant backend implementation |
| `src/lexigram/vector/backends/pgvector/` | PGVector backend implementation |
| `src/lexigram/vector/backends/pinecone/` | Pinecone backend implementation |
| `src/lexigram/vector/backends/chroma.py` | ChromaDB backend implementation |
| `src/lexigram/vector/backends/memory.py` | In-memory backend implementation |
| `src/lexigram/vector/tenancy/` | Tenancy resolver, decorator, and Pinecone namespace resolver |
| `src/lexigram/vector/embedding/client.py` | `OpenAICompatibleEmbeddingClient` |
| `src/lexigram/vector/embedding/cache.py` | Embedding cache implementations |
| `src/lexigram/vector/search/hybrid.py` | Hybrid retrieval and BM25 |
| `src/lexigram/vector/search/reranking.py` | Reranking strategies |
| `src/lexigram/vector/adapters/vector_store.py` | `VectorStoreAdapter` |
| `src/lexigram/vector/adapters/document_store.py` | `DocumentVectorStoreAdapter` |