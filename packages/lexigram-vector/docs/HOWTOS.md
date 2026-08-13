---
title: lexigram-vector How-Tos
description: Task-oriented recipes for common vector store workflows.
sidebar:
  order: 5
---

## Switch Between Backends

Change the `backend` field — the rest of your code stays the same:

```python
# In-memory (testing)
config = VectorConfig(backend="memory")

# pgvector (production)
config = VectorConfig(
    backend="pgvector",
    pgvector__database="primary",
)

# Qdrant (production)
config = VectorConfig(
    backend="qdrant",
    qdrant__url="http://qdrant-cluster:6333",
)
```

## Use Multiple Named Backends

```python
from lexigram.vector import VectorConfig

config = VectorConfig(
    backends=[
        {
            "name": "primary",
            "primary": True,
            "backend": "qdrant",
            "qdrant": {"url": "http://qdrant:6333"},
        },
        {
            "name": "archive",
            "backend": "pgvector",
            "pgvector": {"database": "archive_db"},
        },
    ],
)
```

Resolve by name:

```python
from typing import Annotated
from lexigram.di.markers import Named

primary = await container.resolve(
    Annotated[VectorStoreProtocol, Named("primary")]
)
archive = await container.resolve(
    Annotated[VectorStoreProtocol, Named("archive")]
)
```

## Use Hybrid Search (BM25 + Vector)

```python
from lexigram.vector.search.hybrid import (
    HybridRetriever,
    HybridSearchConfig,
    create_hybrid_retriever,
)

retriever = create_hybrid_retriever(
    vector_store=store,
    config=HybridSearchConfig(
        alpha=0.5,        # Balance between BM25 (0) and vector (1)
        bm25_k1=1.5,      # BM25 saturation parameter
        bm25_b=0.75,      # BM25 length normalization
    ),
)
results = await retriever.search("What is Lexigram?", k=10)
```

## Rerank Search Results

```python
from lexigram.vector.search.reranking import (
    CrossEncoderReranker,
    RerankerPipeline,
    RerankingConfig,
)

reranker = CrossEncoderReranker(
    config=RerankingConfig(model="cross-encoder/ms-marco-MiniLM-L-6-v2")
)
reranked = await reranker.rerank(query="What is Lexigram?", documents=results, top_k=5)

# Or chain rerankers
pipeline = RerankerPipeline(
    rerankers=[SimilarityReranker(), DiversityReranker(diversity_threshold=0.8)]
)
```

## Use the Embedding Client

```python
from lexigram.vector.embedding.client import OpenAICompatibleEmbeddingClient
from lexigram.vector.embedding.config import EmbeddingClientConfig

client = OpenAICompatibleEmbeddingClient(
    config=EmbeddingClientConfig(
        api_base="https://api.openai.com/v1",
        model="text-embedding-3-small",
        dimension=1536,
        api_key="sk-...",
    )
)
embeddings = await client.embed(["Hello world", "Another text"])
```

## Create an AI-Layer Vector Store (with Embeddings)

```python
from lexigram.vector.di.factories import create_vector_store

store = await create_vector_store(
    config=VectorConfig(backend="memory"),
    embedding_fn=client.embed,  # from the embedding client above
)
```

This wraps the infra store in a `VectorStoreAdapter` that auto-generates embeddings for `add_texts()` calls.

## Use MockVectorStore in Tests

```python
from lexigram.vector.testing.mocks import (
    MockVectorStore,
    MockVectorStoreWithErrors,
)

# Simple mock
store = MockVectorStore()
await store.create_collection(CollectionConfig(name="test", dimension=128))

# Mock that simulates failures
error_store = MockVectorStoreWithErrors(
    fail_on=["upsert", "search"]  # raises VectorUpsertError / VectorSearchError
)
```

## Handle Vector Exceptions

```python
from lexigram.vector.exceptions import (
    DimensionMismatchError,
    CollectionNotFoundError,
)

try:
    await collection.search(SearchQuery(vector=[0.1] * 512, top_k=5))
except DimensionMismatchError as e:
    print(f"Expected {e.expected} dimensions, got {e.actual}")
except CollectionNotFoundError as e:
    print(f"Collection {e.collection_name} not found — create it first")
```
