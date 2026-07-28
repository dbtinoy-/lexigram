---
title: lexigram-vector Backends
description: Supported vector store backends in lexigram-vector — pgvector, Pinecone, Qdrant, Chroma, Weaviate, and in-memory
---

`lexigram-vector` provides a unified `VectorStoreProtocol` for vector similarity search across multiple backends. Each backend implements collection management, vector upsert, similarity search, filter compilation, and health checking through the same interface.

## Supported Backends

| Backend | Extra / Package | Production Ready | Best For |
|---------|----------------|-----------------|----------|
| **pgvector** | `[pgvector]` | Yes | PostgreSQL-native, existing pg infra |
| **Qdrant** | `[qdrant]` | Yes | High-performance, rich filtering, gRPC |
| **Pinecone** | `[pinecone]` | Yes | Fully managed, zero-ops vector search |
| **Chroma** | `[chroma]` | Dev/Test | Local dev, ephemeral HTTP or in-memory |
| **Weaviate** | `[weaviate]` | Yes | Hybrid search, graph-backed vector store |
| **Memory** | *(none)* | No | Unit tests, prototyping |

### pgvector

An extension on top of PostgreSQL. Stores vectors in a regular Postgres table with IVFFlat or HNSW indexes. Because it lives in your existing database, pgvector supports transactional consistency, SQL JOINs, and role-based access — no separate cluster to operate. The provider resolves a `DatabaseProviderProtocol` from the DI container at boot time.

```yaml
vector:
  backend: pgvector
  default_dimension: 1536
  default_distance_metric: cosine
  pgvector:
    database: primary
    schema: public
    default_lists: 1000
    create_extension: true
```

```python
from lexigram.vector import VectorProvider, VectorConfig

config = VectorConfig(backend="pgvector")
config.pgvector.database = "primary"
provider = VectorProvider(config=config)
```

### Qdrant

A purpose-built vector database with a rich filtering DSL and configurable gRPC transport. Qdrant supports payload indexing, geo-filters, and quantisation for memory reduction. The gRPC protocol offers lower latency than HTTP for high-throughput workloads.

```yaml
vector:
  backend: qdrant
  qdrant:
    url: http://localhost:6333
    prefer_grpc: true
    grpc_port: 6334
```

### Pinecone

A fully managed vector database requiring zero operational overhead. Configure the API key, environment, and index name. Pinecone handles replication, scaling, and index optimisation automatically. Best when you want to outsource vector infrastructure entirely.

```yaml
vector:
  backend: pinecone
  pinecone:
    api_key: "${PINECONE_API_KEY}"
    environment: us-west1-gcp
    index_name: my-embeddings
    namespace: default
```

### Chroma

An open-source embedding database that can run in-memory (ephemeral client) or as a client to a Chroma server. The `use_http_client: false` setting switches to an in-process `EphemeralClient`, making Chroma convenient for local development without external dependencies.

```yaml
vector:
  backend: chroma
  chroma:
    host: localhost
    port: 8000
    use_http_client: false
```

:::caution
Chroma is flagged by `validate_for_environment(Environment.PRODUCTION)` — it is not recommended for production deployments.
:::

### Weaviate

A vector search engine that combines vector similarity with keyword BM25 hybrid search out of the box. Weaviate supports multi-tenancy, cross-referencing between objects, and GraphQL-native querying. The backend uses gRPC for vector operations and HTTP for schema management.

```yaml
vector:
  backend: weaviate
  weaviate:
    url: http://localhost:8080
    grpc_port: 50051
    api_key: "${WEAVIATE_API_KEY}"
```

### Memory

An in-process dictionary-backed store. Configurable limits on collection count and max vectors per collection. All data is lost on process restart.

```yaml
vector:
  backend: memory
  memory:
    max_collections: 100
    max_vectors_per_collection: 100000
```

## Dimension Config & Embedding Integration

The `default_dimension` field on `VectorConfig` controls the vector size for new collections. This must match the output dimension of your embedding model. Common values:

| Model | Dimension |
|-------|-----------|
| `text-embedding-3-small` | 1536 |
| `text-embedding-3-large` | 3072 |
| `text-embedding-ada-002` | 1536 |
| `gte-small` | 384 |

`lexigram-vector` provides an `OpenAICompatibleEmbeddingClient` for generating embeddings before upsert, and `EmbeddingCache` to avoid re-computing embeddings for duplicate content.

```yaml
vector:
  default_dimension: 1536
  enable_cache: true
  cache_ttl: 86400
  embedding_model: text-embedding-3-small
```

## Quick Selection Guide

| If you need… | Choose… |
|-------------|---------|
| ACID-compliant vectors in Postgres | pgvector |
| High-throughput with rich filters | Qdrant |
| Fully managed, zero ops | Pinecone |
| Local dev / ephemeral only | Memory or Chroma |
| Hybrid vector + keyword search | Weaviate |

## Multi-Backend Configuration

```yaml
vector:
  backends:
    - name: primary
      primary: true
      backend: qdrant
      qdrant:
        url: http://qdrant-primary:6333
    - name: rag
      backend: pgvector
      pgvector:
        database: rag
```

## Testing with Memory Backend

```python
from lexigram.vector import VectorProvider, VectorConfig

provider = VectorProvider(config=VectorConfig(backend="memory"))
```
