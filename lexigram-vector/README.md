# lexigram-vector

Vector storage infrastructure for the Lexigram Framework with Qdrant, ChromaDB,
PGVector, Pinecone, and in-memory backends. Provides embedding clients, vector
search, hybrid retrieval, reranking, and Named DI multi-store support.


> Full documentation: [docs.lexigram.dev](https://docs.lexigram.dev)
## Install

```bash
uv add lexigram lexigram-vector

# With Qdrant support
uv add qdrant-client

# With ChromaDB support
uv add chromadb

# With PGVector support
uv add pgvector  # Requires lexigram-sql for database access

# With Pinecone support
uv add pinecone-client

# With embedding support
uv add openai  # or anthropic, cohere, etc.
```

## Quick Start

```python
from __future__ import annotations

import asyncio

from lexigram import Application
from lexigram.contracts.data.vector.protocols import VectorStoreProtocol
from lexigram.di.module import Module, module
from lexigram.vector import VectorModule
from lexigram.vector.config import QdrantConfig, VectorConfig


@module(
    imports=[
        VectorModule.configure(
            VectorConfig(
                backend="qdrant",
                qdrant=QdrantConfig(
                    url="http://localhost:6333",
                ),
            )
        )
    ]
)
class AppModule(Module):
    pass


async def main() -> None:
    async with Application.boot(modules=[AppModule]) as app:
        store = await app.container.resolve(VectorStoreProtocol)
        
        # Create a collection
        await store.create_collection(
            name="documents",
            dimension=1536,
        )
        
        # Upsert vectors
        await store.upsert(
            collection_name="documents",
            ids=["doc1", "doc2"],
            vectors=[[0.1] * 1536, [0.2] * 1536],
            metadata=[
                {"title": "Document 1", "category": "tech"},
                {"title": "Document 2", "category": "science"},
            ],
        )
        
        # Search
        results = await store.search(
            collection_name="documents",
            query_vector=[0.15] * 1536,
            limit=5,
        )
        
        for result in results:
            print(f"{result.id}: {result.metadata['title']} (score: {result.score})")


if __name__ == "__main__":
    asyncio.run(main())
```

## What It Provides

`lexigram-vector` ships with:

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

**Architecture note**: This package provides infrastructure and data-layer
functionality for vector storage and retrieval. While it is commonly used by AI
and RAG features (`lexigram-ai-rag`), it is a general-purpose vector database
abstraction suitable for any use case requiring semantic search, similarity
matching, or high-dimensional data storage.

## Configuration

> **Zero-config usage:** Call `VectorModule.configure()` with no arguments to start
> with all built-in defaults — no config file or environment variables needed.
> See the [Config reference](#config-reference) below for all default values.

```python
from lexigram.vector import VectorModule

app.add_module(VectorModule.configure())  # all defaults
```

### Option 1 — YAML file *(use when config lives in a single explicit file)*

Declare config in a YAML file loaded at a fixed, explicit path.  `LEX_*`
environment variables override YAML values at startup.  Use this for **local
development, simple self-hosted setups, or when you control exactly which
file is loaded**.  For multi-environment deployments (staging, production)
prefer **Option 2**, which automatically selects the right profile file.

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

---

### Option 2 — Profiles + Environment Variables *(recommended for production, staging, Docker, CI/CD)*

Loads a base `application.yaml`, then overlays an environment-specific
file (`application.production.yaml`, `application.staging.yaml`, etc.)
based on the `LEX_PROFILE` environment variable.  `LEX_*` env vars are
applied last as the final override layer.  Use this in **production,
staging, Docker, Kubernetes, and CI/CD pipelines** — set
`LEX_PROFILE=production` and the right profile file loads automatically.

`section` is optional: specify it (e.g. `section="vector"`) when this
package's config is nested inside a shared `application.yaml`; omit it
when the file is dedicated to this package alone.

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

---
### Option 3 — Python *(use when config is dynamic or computed at boot)*

Build config in code at boot time. Use this when settings are **derived at
runtime** — e.g. secrets fetched from a vault, per-tenant configurations,
or when you need multiple module instances with different settings.

```python
from lexigram.vector import VectorModule
from lexigram.vector.config import QdrantConfig, VectorConfig

app.add_module(VectorModule.configure(
    VectorConfig(
        backend="qdrant",
        qdrant=QdrantConfig(
            url="http://localhost:6333",
        ),
    )
))
```

---

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
| `retry_delay` | `1.0` | `LEX_VECTOR__RETRY_DELAY` | Delay between retries in seconds |
| `pgvector` | `PgVectorConfig()` | — | PGVector-specific settings |
| `pinecone` | `PineconeConfig()` | — | Pinecone-specific settings |
| `qdrant` | `QdrantConfig()` | — | Qdrant-specific settings |
| `memory` | `MemoryConfig()` | — | In-memory-specific settings |
| `backends` | `[]` | — | List of `NamedVectorConfig` entries for multi-store support |
| `tenancy` | `None` | — | `VectorTenancyConfig` for per-tenant collection isolation |

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
| `default_ef_search` | `40` | `LEX_VECTOR__PGVECTOR__DEFAULT_EF_SEARCH` | Default ef_search for HNSW index |
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
from lexigram.di.named import Named


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

### VectorModule.configure(config=None, enable_reranking=False)

Create a `VectorModule` with explicit configuration.

**Args**:
- `config`: `VectorConfig` instance, `dict` of config values, or `None` to use environment variable defaults
- `enable_reranking`: Enable cross-encoder reranking of retrieval results (default: `False`)

**Returns**: `DynamicModule` that registers `VectorStoreProtocol` and `VectorCollectionProtocol`

**Exports**: `VectorStoreProtocol`, `VectorCollectionProtocol`

**Example**:

```python
from lexigram.vector import VectorModule
from lexigram.vector.config import QdrantConfig, VectorConfig

@module(
    imports=[
        VectorModule.configure(
            VectorConfig(
                backend="qdrant",
                qdrant=QdrantConfig(url="http://localhost:6333"),
            ),
            enable_reranking=True,
        )
    ]
)
class AppModule(Module):
    pass
```

### VectorModule.stub(config=None)

Create a `VectorModule` suitable for unit and integration testing. Uses an
in-memory backend with no external service dependencies.

**Args**:
- `config`: Optional `VectorConfig` override (uses safe in-memory defaults when `None`)

**Returns**: `DynamicModule` that registers `VectorStoreProtocol` and `VectorCollectionProtocol`

**Example**:

```python
from lexigram.vector import VectorModule

async def test_vector_search():
    async with Application.boot(
        modules=[VectorModule.stub()]
    ) as app:
        store = await app.container.resolve(VectorStoreProtocol)
        # Test with in-memory backend
```

## Vector Store Operations

### Create Collection

```python
from lexigram.contracts.data.vector.enums import DistanceMetric, IndexType

await store.create_collection(
    name="documents",
    dimension=1536,
    distance_metric=DistanceMetric.COSINE,
    index_type=IndexType.HNSW,
)
```

### Upsert Vectors

```python
await store.upsert(
    collection_name="documents",
    ids=["doc1", "doc2", "doc3"],
    vectors=[
        [0.1] * 1536,
        [0.2] * 1536,
        [0.3] * 1536,
    ],
    metadata=[
        {"title": "Doc 1", "category": "tech"},
        {"title": "Doc 2", "category": "science"},
        {"title": "Doc 3", "category": "tech"},
    ],
)
```

### Search with Filters

```python
results = await store.search(
    collection_name="documents",
    query_vector=[0.15] * 1536,
    limit=10,
    filter={"category": "tech"},  # Metadata filter
)

for result in results:
    print(f"{result.id}: score={result.score}, metadata={result.metadata}")
```

### Delete Vectors

```python
await store.delete(
    collection_name="documents",
    ids=["doc1", "doc2"],
)
```

## Embedding Client

Generate embeddings with an OpenAI-compatible client:

```python
from lexigram.vector.embedding.client import OpenAICompatibleEmbeddingClient
from lexigram.vector.embedding.config import EmbeddingClientConfig

client = OpenAICompatibleEmbeddingClient(
    config=EmbeddingClientConfig(
        api_key="your-api-key",
        model="text-embedding-ada-002",
    )
)

# Single text
embedding = await client.embed("Hello, world!")

# Batch
embeddings = await client.embed_batch(["Text 1", "Text 2", "Text 3"])
```

## Embedding Cache

Cache embeddings to reduce API calls:

```python
from lexigram.vector.embedding.cache import InMemoryEmbeddingCache

cache = InMemoryEmbeddingCache(max_size=10000)

# Cache hit on second call
embedding1 = await client.embed("Hello, world!")
await cache.set("Hello, world!", embedding1)

embedding2 = await cache.get("Hello, world!")  # From cache
```

## Hybrid Retrieval

Combine BM25 and vector search with reciprocal rank fusion:

```python
from lexigram.vector.search.hybrid import HybridRetriever, HybridSearchConfig

retriever = HybridRetriever(
    vector_store=store,
    config=HybridSearchConfig(
        collection_name="documents",
        alpha=0.5,  # Weight between BM25 (0.0) and vector (1.0)
        k=60,       # RRF parameter
    ),
)

results = await retriever.search(
    query="machine learning",
    query_vector=[0.1] * 1536,
    limit=10,
)
```

## Reranking

Rerank search results for improved relevance:

```python
from lexigram.vector.search.reranking import (
    CrossEncoderReranker,
    RerankerPipeline,
    RerankingConfig,
)

reranker = CrossEncoderReranker(
    config=RerankingConfig(
        model_name="cross-encoder/ms-marco-MiniLM-L-6-v2",
    )
)

# Rerank results
reranked = await reranker.rerank(
    query="machine learning",
    results=search_results,
    limit=5,
)
```

Compose multiple rerankers in a pipeline:

```python
from lexigram.vector.search.reranking import (
    CrossEncoderReranker,
    DiversityReranker,
    RerankerPipeline,
)

pipeline = RerankerPipeline(
    rerankers=[
        CrossEncoderReranker(config=cross_encoder_config),
        DiversityReranker(lambda_param=0.5),
    ]
)

reranked = await pipeline.rerank(query="machine learning", results=results)
```

## Adapters

Use adapters to bridge vector stores with other abstractions:

### VectorStoreAdapter

```python
from lexigram.vector.adapters.vector_store import VectorStoreAdapter

adapter = VectorStoreAdapter(store=store)

# Higher-level operations
await adapter.index_documents(
    collection_name="documents",
    documents=[
        {"id": "doc1", "text": "Document 1", "metadata": {...}},
        {"id": "doc2", "text": "Document 2", "metadata": {...}},
    ],
    embedding_fn=client.embed_batch,
)
```

### DocumentVectorStoreAdapter

```python
from lexigram.vector.adapters.document_store import DocumentVectorStoreAdapter

adapter = DocumentVectorStoreAdapter(
    vector_store=store,
    document_store=nosql_store,
)

# Store documents in NoSQL and vectors in vector store
await adapter.index_with_metadata(
    collection_name="documents",
    documents=[...],
    embedding_fn=client.embed_batch,
)
```

## Integration with AI and RAG

While `lexigram-vector` is a general-purpose vector storage layer, it integrates
seamlessly with AI and RAG features:

- **`lexigram-ai-rag`** — Uses `VectorStoreProtocol` for retrieval-augmented generation
- **`lexigram-ai`** — Uses embedding clients and vector stores for semantic search and memory
- **`lexigram-cache`** — Can use `SemanticCacheProtocol` (backed by vector stores) for semantic caching

The Named DI system allows you to use different vector stores for different
purposes (e.g., `primary` for semantic search, `rag` for retrieval, `cache` for
semantic caching).

## Multi-Tenancy

`lexigram-vector` supports per-tenant isolation via resolved collection names.
When tenancy is enabled, every collection name is resolved through a
`TenantCollectionResolver`, producing a tenant-specific physical name.

### Configuration

Add `tenancy` to `VectorConfig`:

```python
from lexigram.vector.config import VectorTenancyConfig, VectorConfig, VectorModule

config = VectorConfig(
    backend="qdrant",
    tenancy=VectorTenancyConfig(
        enabled=True,
        template="{logical}_{tenant}",  # default
    ),
)
VectorModule.configure(config)
```

### How It Works

| Component | Role |
|-----------|------|
| `VectorTenancyConfig` | Dataclass with `enabled` flag and `template` string |
| `TemplatedTenantCollectionResolver` | Resolves `{logical}_{tenant}` → physical name |
| `PineconeNamespaceTenantResolver` | Pinecone-specific namespace resolution |
| `TenantVectorStoreDecorator` | Wraps any `VectorStoreProtocol`, resolves names per-tenant |

The decorator reads `tenant_id` from the ambient context
(`lexigram.primitives.context.TENANT_ID`). Tenants with the same logical
collection name resolve to different physical collections — data is
fully isolated.

## Key Source Files

- `src/lexigram/vector/module.py` — `VectorModule.configure()`, `.stub()`
- `src/lexigram/vector/config.py` — `VectorConfig`, `VectorTenancyConfig`, `NamedVectorConfig`, backend configs
- `src/lexigram/vector/di/provider.py` — `VectorProvider` boot and registration
- `src/lexigram/vector/di/factories.py` — Factory functions for creating vector stores
- `src/lexigram/vector/backends/qdrant/` — Qdrant backend implementation
- `src/lexigram/vector/backends/pgvector/` — PGVector backend implementation
- `src/lexigram/vector/backends/pinecone/` — Pinecone backend implementation
- `src/lexigram/vector/backends/chroma.py` — ChromaDB backend implementation
- `src/lexigram/vector/backends/memory.py` — In-memory backend implementation
- `src/lexigram/vector/tenancy/` — Tenancy resolver, decorator, and Pinecone namespace resolver
- `src/lexigram/vector/embedding/client.py` — `OpenAICompatibleEmbeddingClient`
- `src/lexigram/vector/embedding/cache.py` — Embedding cache implementations
- `src/lexigram/vector/search/hybrid.py` — Hybrid retrieval and BM25
- `src/lexigram/vector/search/reranking.py` — Reranking strategies
- `src/lexigram/vector/adapters/vector_store.py` — `VectorStoreAdapter`
- `src/lexigram/vector/adapters/document_store.py` — `DocumentVectorStoreAdapter`
