# Saga Selection Guide

> **Decision framework:** Which saga pattern to use, and how to migrate between them.

## Quick Decision

| You need... | Use... |
|---|---|
| Simple sequential steps with compensation | `AbstractSaga` |
| Idempotent, compute-heavy steps (LLM calls, RAG, embeddings) | `ContentAddressedSaga` |
| Batch processing of independent items | `SagaBatchProcessor` |

## AbstractSaga (Standard)

**When to use:**

- Steps have side effects that require compensation (API calls, database writes)
- Each step is cheap or must run every time
- You need fine-grained `SagaStep` control with named steps

```python
class OrderSaga(AbstractSaga[None]):
    def __init__(self, order_id: str, service: OrderService) -> None:
        super().__init__()
        self.add_step(SagaStep(...))
```

**Limitations:**

- No caching — every execute runs every step
- No content-addressed deduplication
- Steps run unconditionally

## ContentAddressedSaga (Cached)

**When to use:**

- Steps are **idempotent** — same inputs → same output
- Steps are **expensive** — LLM calls, embeddings, RAG retrieval
- You want to **resume** sagas without re-executing completed stages
- You have **tenant isolation** requirements (cache keys include tenant ID)

```python
saga = ContentAddressedSaga(
    saga_id="gen-embed-123",
    checkpoint_store=InMemoryContentCheckpointStore(),
    tenant_id="tenant-abc",
)
saga.add_stage(ContentAddressedStage("embed", embed_handler, "v1"))
```

### How it works

1. Before running a stage, `ContentAddressedSaga` computes `sha256(stage_id || tenant_id || inputs || handler_version || config)`.
2. If the checkpoint store has a matching entry, the cached output is returned immediately.
3. On cache miss, the handler runs and the result is stored keyed by the content hash.

### Version invalidation

Changing `handler_version` or `config_affecting_output` produces a different key — old cache entries are automatically ignored. This is how you invalidate caches when handler logic or configuration changes.

### Backend stores

| Store | Backend | Use Case |
|---|---|---|
| `InMemoryContentCheckpointStore` | `dict` | Unit tests, prototypes |
| `CacheContentCheckpointStore` | `CacheBackendProtocol` (Redis, etc.) | Stateless apps, fast TTL-based expiry |
| `DatabaseContentCheckpointStore` | `DatabaseProviderProtocol` (Postgres, etc.) | Durable persistence, audit trails |

### Configuration

```python
from lexigram.workflow.config import ContentCheckpointConfig

config = ContentCheckpointConfig(
    enabled=True,
    inline_threshold_bytes=1_048_576,  # Offload outputs >1 MB to blob store
    default_ttl_seconds=86400,         # 24-hour default TTL
)
```

## Batch Processing

Use `SagaBatchProcessor` when you have many independent items that each go through the same saga workflow (e.g., process 10,000 orders, each as its own saga).

## Migration: AbstractSaga → ContentAddressedSaga

1. Replace `SagaStep` with `ContentAddressedStage`.
2. Assign a `handler_version` (bump when handler logic changes).
3. Provide a `ContentCheckpointStoreProtocol` implementation.
4. (Optional) Add `config_affecting_output` for configuration-based cache invalidation.
