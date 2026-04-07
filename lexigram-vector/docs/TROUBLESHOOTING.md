---
title: lexigram-vector Troubleshooting
description: Common errors, causes, and fixes.
sidebar:
  order: 6
---

## `VectorConnectionError` — Failed to connect

**Exception:** `lexigram.vector.exceptions.VectorConnectionError`

**Cause:** Backend service is unreachable — wrong URL, port, or the service isn't running.

**Fix:**
- Verify the backend is running (`docker ps`, `curl <url>/health`).
- Check `url`, `host`, `port` in `VectorConfig`.
- For pgvector, ensure the database is accessible and the extension is installed.

## `CollectionNotFoundError` — Collection doesn't exist

**Exception:** `lexigram.vector.exceptions.CollectionNotFoundError`

**Cause:** Tried to `get_collection()`, `search()`, or `delete()` on a collection that hasn't been created yet.

**Fix:**
```python
if await store.collection_exists("my_docs"):
    collection = await store.get_collection("my_docs")
else:
    await store.create_collection(CollectionConfig(name="my_docs", dimension=1536))
```

## `DimensionMismatchError` — Wrong vector dimension

**Exception:** `lexigram.vector.exceptions.DimensionMismatchError`

**Cause:** The vector you're upserting or searching with has a different dimensionality than the collection.

**Fix:**
- Check `default_dimension` in `VectorConfig`.
- Ensure your embedding model produces the correct dimension.
- Create collections with explicit `dimension` matching your embeddings.

```python
# The error tells you the exact mismatch
try:
    await collection.upsert([record])
except DimensionMismatchError as e:
    print(f"Expected {e.expected}, got {e.actual}")
```

## `VectorStoreProtocol resolved before VectorProvider.boot() completed`

**Runtime error (not an exception class)**

**Cause:** Something in your code resolved `VectorStoreProtocol` before the provider booted (e.g., in a `register()` method of another provider).

**Fix:** Move resolution to `boot()` methods. The container is not ready for resolution during `register()`.

## `Unknown vector backend` — Backend not supported

**ValueError** raised from `VectorProvider._create_store()`

**Cause:** `VectorConfig.backend` is set to an unsupported value.

**Fix:** Use one of: `memory`, `pgvector`, `qdrant`, `pinecone`, `chroma`, `weaviate`.

## Missing backend driver package

**Cause:** Backend dependency not installed (e.g., `qdrant-client` for Qdrant).

**Fix:**
```bash
uv add "lexigram-vector[qdrant]"
```

The provider logs `vector_store_connected` at info level on successful connection — if you don't see it, check the package is installed.

## Health check returns `DEGRADED`

**Cause:** The vector store is booted but the health ping failed (e.g., connection timeout).

**Fix:**
- Check network connectivity between your app and the backend.
- Adjust `health_check(timeout)` parameter.
- Review the details dict in `HealthCheckResult.details` for per-backend status.

## pgvector: "relation does not exist"

**Cause:** The pgvector extension hasn't been created, or the default schema is wrong.

**Fix:**
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```
Or set `create_extension: true` in `PgVectorConfig` (default).
Check `schema` in `PgVectorConfig` matches your database setup.

## CollectionAlreadyExistsError

**Symptom:** `CollectionAlreadyExistsError: Collection 'my_docs' already exists`

**Cause:** `create_collection` was called with a name that already exists.

**Solution:** Check existence first, or use `get_or_create_collection` where available.

```python
if await store.collection_exists("my_docs"):
    collection = await store.get_collection("my_docs")
else:
    collection = await store.create_collection(
        CollectionConfig(name="my_docs", dimension=1536)
    )
```

## Pinecone authentication failure

**Symptom:** `VectorConnectionError: Pinecone API key invalid` or `401 Unauthorized`

**Cause:** The Pinecone API key is missing, expired, or the environment does not match the index.

**Solution:** Verify `api_key` and `environment` in `PineconeConfig`. In production, set via environment variable — `validate_for_environment()` catches a missing key.

```yaml
vector:
  backend: pinecone
  pinecone:
    api_key: "${PINECONE_API_KEY}"
    environment: us-west1-gcp
    index_name: my-embeddings
```

## Filter compilation error across backends

**Symptom:** `FilterCompilationError: [qdrant] Filter compilation failed: Unsupported operator 'regex'`

**Cause:** The metadata filter uses an operator not supported by the target backend. Each backend has different filter capabilities.

**Solution:** Check the backend's supported operators. pgvector supports basic comparisons, Qdrant supports nested conditions, Pinecone uses metadata dictionaries, Chroma supports `$and`/`$or`/`$eq`.

```python
from lexigram.contracts.data.vector.filters import Filter

# Qdrant-friendly compound filter
filter = Filter.eq("category", "science") & Filter.gte("score", 0.5)

# Chroma does not support $ne
filter = Filter.eq("status", "active")
```

## VectorUpsertError — Batch size exceeds limit

**Symptom:** `VectorUpsertError: Batch upsert failed: Payload exceeds 2 MB limit`

**Cause:** The upsert batch contains too many vectors or vectors with large metadata, exceeding the backend's per-request limit.

**Solution:** Reduce `upsert_batch_size` in `VectorConfig`. Pinecone and Qdrant have ~2 MB per-request limits.

```python
from lexigram.vector.config import VectorConfig

config = VectorConfig(backend="pinecone", upsert_batch_size=20)
```

## Chroma HTTP connection refused

**Symptom:** `VectorConnectionError: Cannot connect to Chroma at localhost:8000 — Connection refused`

**Cause:** Chroma is configured with `use_http_client: true` but no Chroma server is running on that host/port.

**Solution:** Start a Chroma server (`chroma run`) or switch to the ephemeral in-memory client for development.

```yaml
vector:
  backend: chroma
  chroma:
    use_http_client: false   # In-memory EphemeralClient for local dev
```

Note: Chroma is flagged by `validate_for_environment(Environment.PRODUCTION)` — not recommended for production.
