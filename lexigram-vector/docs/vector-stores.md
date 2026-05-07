# Vector Stores in lexigram-vector

Deep-dive companion to the `lexigram-vector` README: store operations, embedding clients and caches, hybrid retrieval, reranking, adapters, AI/RAG integration, and multi-tenancy.

---

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
from lexigram.vector import VectorModule
from lexigram.vector.config import VectorTenancyConfig, VectorConfig

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