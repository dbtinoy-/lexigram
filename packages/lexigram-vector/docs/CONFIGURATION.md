---
title: lexigram-vector Configuration
description: All configuration keys for VectorConfig and driver-specific configs.
sidebar:
  order: 4
---

Configuration section: `vector` (in `application.yaml`) or env prefix `LEX_VECTOR__`.

The provider's `config_key = "vector"`. The orchestrator reads the `vector:` section from YAML and coerces it into `VectorConfig`.

---

## VectorConfig

Full example:

```yaml
vector:
  enabled: true
  backend: qdrant
  default_distance_metric: cosine
  default_index_type: hnsw
  default_dimension: 1536
  upsert_batch_size: 100
  max_retries: 3
  retry_delay: 0.5
  collection_name: default
  enable_cache: false
  cache_ttl: 86400
  embedding_model: text-embedding-3-small
  pgvector:
    database: primary
    schema: public
  qdrant:
    url: http://localhost:6333
    prefer_grpc: true
  pinecone:
    environment: us-west1-gcp
    index_name: my_index
  backends:
    - name: primary
      primary: true
      backend: qdrant
      qdrant:
        url: http://qdrant:6333
    - name: archive
      backend: pgvector
      pgvector:
        database: archive
```

Env-var override form:

```bash
export LEX_VECTOR__BACKEND=pgvector
export LEX_VECTOR__DEFAULT_DIMENSION=768
export LEX_VECTOR__PGVECTOR__DATABASE=primary
```

### Top-Level Fields

| Key | Type | Default | Env Var | Description |
|-----|------|---------|---------|-------------|
| `enabled` | `bool` | `True` | `LEX_VECTOR__ENABLED` | Enable vector subsystem |
| `backend` | `str` | `"memory"` | `LEX_VECTOR__BACKEND` | Driver: `memory`, `pgvector`, `qdrant`, `pinecone`, `chroma`, `weaviate` |
| `default_distance_metric` | `DistanceMetric` | `"cosine"` | `LEX_VECTOR__DEFAULT_DISTANCE_METRIC` | `cosine`, `euclidean`, `dot_product` |
| `default_index_type` | `IndexType` | `"hnsw"` | `LEX_VECTOR__DEFAULT_INDEX_TYPE` | `hnsw`, `ivfflat` |
| `default_dimension` | `int` | `1536` | `LEX_VECTOR__DEFAULT_DIMENSION` | Default vector dimension |
| `upsert_batch_size` | `int` | `100` | `LEX_VECTOR__UPSERT_BATCH_SIZE` | Vectors per upsert batch |
| `max_retries` | `int` | `3` | `LEX_VECTOR__MAX_RETRIES` | Operation retries |
| `retry_delay` | `float` | `0.5` | `LEX_VECTOR__RETRY_DELAY` | Delay between retries (seconds) |
| `collection_name` | `str` | `"default"` | `LEX_VECTOR__COLLECTION_NAME` | Default collection for AI-layer ops |
| `enable_cache` | `bool` | `False` | `LEX_VECTOR__ENABLE_CACHE` | Embedding cache (requires `CacheBackendProtocol`) |
| `cache_ttl` | `int` | `86400` | `LEX_VECTOR__CACHE_TTL` | Cache TTL (seconds) |
| `embedding_model` | `str` | `"text-embedding-3-small"` | `LEX_VECTOR__EMBEDDING_MODEL` | Model name for AI-layer embedding |

### Driver-Specific Configs

#### PgVectorConfig (`pgvector.`)

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `database` | `str` | `"primary"` | Database backend name from `db.backends` |
| `schema` | `str` | `"public"` | Database schema for vector tables |
| `default_lists` | `int` | `100` | Lists for IVFFlat index |
| `default_probes` | `int` | `10` | Probes for IVFFlat index |
| `default_ef_search` | `int` | `64` | ef_search for HNSW index |
| `table_prefix` | `str` | `"vec_"` | Table name prefix |
| `create_extension` | `bool` | `True` | Auto-create pgvector extension |

#### QdrantConfig (`qdrant.`)

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `url` | `str` | `"http://localhost:6333"` | Server URL |
| `api_key` | `SecretStr \| None` | `None` | API key |
| `grpc_port` | `int` | `6334` | gRPC port |
| `prefer_grpc` | `bool` | `True` | Prefer gRPC over HTTP |
| `timeout` | `float` | `30.0` | Request timeout |

#### PineconeConfig (`pinecone.`)

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `api_key` | `SecretStr` | `""` | Pinecone API key |
| `environment` | `str` | `""` | Environment (e.g. `us-west1-gcp`) |
| `index_name` | `str` | `""` | Index name |
| `namespace` | `str` | `""` | Default namespace |
| `timeout` | `float` | `30.0` | Request timeout |
| `pool_threads` | `int` | `4` | Connection pool threads |

#### ChromaConfig (`chroma.`)

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `host` | `str` | `"localhost"` | Server host |
| `port` | `int` | `8000` | Server port |
| `use_http_client` | `bool` | `True` | False = ephemeral in-memory client |
| `api_key` | `SecretStr \| None` | `None` | API key |
| `collection_name` | `str` | `"default"` | Default collection |
| `timeout` | `float` | `30.0` | Request timeout |

#### WeaviateConfig (`weaviate.`)

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `url` | `str` | `"http://localhost:8080"` | Cluster URL |
| `api_key` | `SecretStr \| None` | `None` | API key |
| `grpc_port` | `int` | `50051` | gRPC port |
| `timeout` | `float` | `30.0` | Request timeout |

#### MemoryConfig (`memory.`)

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `max_collections` | `int` | `100` | Max in-memory collections |
| `max_vectors_per_collection` | `int` | `100000` | Max vectors per collection |

---

## Multi-Backend Config

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

Env-var form for named backends uses indexed arrays (not recommended for complex configs — use YAML).

---

## Environment Variables

All keys map from env vars using `LEX_VECTOR__` prefix with `__` as nested delimiter:

```bash
export LEX_VECTOR__BACKEND=pgvector
export LEX_VECTOR__DEFAULT_DIMENSION=1536
export LEX_VECTOR__PGVECTOR__DATABASE=primary
export LEX_VECTOR__QDRANT__URL=http://qdrant:6333
export LEX_VECTOR__ENABLE_CACHE=true
export LEX_VECTOR__EMBEDDING_MODEL=text-embedding-3-small
```

Embedding client config uses a separate prefix: `LEX_VECTOR__EMBEDDING__`.
