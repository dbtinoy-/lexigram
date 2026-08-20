---
title: "Retrieval-Augmented Generation"
description: "Chunk, embed, retrieve, and synthesize with the RAG pipeline protocol."
---

`lexigram-ai-rag` provides a configurable RAG pipeline that ingests documents, chunks them, generates embeddings, retrieves relevant context, and synthesizes grounded answers. The pipeline is protocol-driven: swap chunking strategies, retrieval backends, and synthesis models without changing application code.

For the full configuration reference and advanced features (HyDE, reranking, evaluation), see the [`lexigram-ai-rag` package docs](/packages/lexigram-ai-rag/).

---

## 1. The Contracts

The RAG system is built on protocols from `lexigram.contracts.ai.rag`. Every pipeline operation returns a `Result` so failures are explicit:

```python
from typing import Any, Protocol, runtime_checkable
from lexigram.result import Result
from lexigram.contracts.ai.rag import RAGContext, RAGResponse, RAGError
from lexigram.contracts.ai.vector import SearchResultProtocol


class RAGPipelineProtocol(Protocol):
    async def execute(self, context: RAGContext) -> Result[RAGResponse, RAGError]: ...


class RetrievalStrategyProtocol(Protocol):
    async def retrieve(
        self,
        query: str,
        candidates: list[SearchResultProtocol],
        *,
        top_k: int = 5,
        **kwargs: Any,
    ) -> list[SearchResultProtocol]: ...
```

`RAGContext` carries the query and optional filters, and `RAGResponse` contains the synthesized answer with sources and citations:

```python
from dataclasses import dataclass
from typing import Any
from lexigram.contracts.ai.vector import SearchResultProtocol


@dataclass(frozen=True)
class RAGContext:
    query: str
    config: dict[str, Any] | None = None
    filters: dict[str, Any] | None = None
    session_id: str | None = None


@dataclass(frozen=True)
class RAGResponse:
    answer: str
    sources: list[SearchResultProtocol]
    citations: list[Any] | None = None
    confidence: float | None = None
```

---

## 2. Configuration

Add the `RAGModule` and configure chunking, retrieval, and synthesis:

```python
from lexigram import Application
from lexigram.ai.rag import RAGModule, RAGConfig

app = Application(name="my-app")
app.add_module(RAGModule.configure(
    RAGConfig(
        chunk_size=512,
        chunk_overlap=50,
        embedding_provider="openai",
        top_k=5,
        enable_citations=True,
        collection_name="knowledge_base",
    ),
))
```

```yaml title="application.yaml"
ai_rag:
  enabled: true
  vector_store_type: pgvector
  collection_name: knowledge_base
  top_k: 5
  chunk_size: 512
  chunk_overlap: 50
  chunking_strategy: recursive
  embedding_provider: openai
  embedding_model: text-embedding-3-small
  enable_citations: true
  enable_hyde: false
  enable_query_expansion: true
  use_hybrid_search: true
  similarity_threshold: 0.7
  enable_caching: true
  cache_ttl: 3600
```

:::tip
Set `embedding_model` explicitly — there is no vendor-specific default. For OpenAI use `text-embedding-3-small` or `text-embedding-3-large`.
:::

---

## 3. Chunking Strategies

The pipeline supports multiple chunking strategies configured via `chunking_strategy`:

| Strategy | Description |
|----------|-------------|
| `recursive` | Recursive character splitting with overlap (default) |
| `token` | Token-aware splitting at model boundaries |
| `semantic` | Semantic boundary detection using embeddings |

Use the `create_chunker` factory for programmatic access:

```python
from lexigram.ai.rag import create_chunker
from lexigram.ai.rag.chunking import ChunkingConfig, ChunkingStrategy

chunker = create_chunker(
    ChunkingStrategy.RECURSIVE,
    ChunkingConfig(
        chunk_size=512,
        overlap=50,
    ),
)
chunks = await chunker.chunk(document_text)
```

---

## 4. Indexing Documents

Ingest documents into the vector store through the pipeline. Documents are chunked, embedded, and stored automatically:

```python
from lexigram.ai.rag import RAGModule, RAGPipeline, RAGConfig
from lexigram.contracts.ai.rag import RAGPipelineProtocol


async def index_documents() -> None:
    async with Application.boot(
        modules=[RAGModule.configure(RAGConfig(collection_name="kb"))]
    ) as app:
        pipeline = await app.container.resolve(RAGPipelineProtocol)

        # Documents are chunked, embedded, and indexed automatically
        result = await pipeline.execute(
            RAGContext(query="seed document", config={"index_only": True})
        )
```

:::note
For bulk ingestion, configure `vector_store_type`, `collection_name`, and `embedding_provider` to match your vector store backend. The pipeline delegates embedding to the configured provider and stores vectors in the specified collection.
:::

---

## 5. Querying

Run a RAG query to retrieve relevant documents and synthesize an answer:

```python
from lexigram import Application
from lexigram.ai.rag import RAGModule, RAGConfig
from lexigram.contracts.ai.rag import RAGPipelineProtocol, RAGContext


async def ask(query: str) -> None:
    async with Application.boot(
        modules=[RAGModule.configure(RAGConfig(top_k=5))]
    ) as app:
        pipeline = await app.container.resolve(RAGPipelineProtocol)

        result = await pipeline.execute(RAGContext(query=query))
        if result.is_ok():
            response = result.unwrap()
            print(f"Answer: {response.answer}")
            for source in response.sources:
                print(f"  Source: {source}")
            if response.citations:
                for citation in response.citations:
                    print(f"  Citation: {citation}")
        else:
            error = result.unwrap_err()
            print(f"RAG failed: {error}")
```

When `enable_citations` is `True`, sources are cited inline in the response. The `sources` list contains `SearchResultProtocol` objects with metadata about each retrieved document.

---

## 6. Retrieval Strategies

The pipeline uses `RetrievalStrategyProtocol` for pluggable retrieval. The strategy registry (`RetrievalStrategyRegistry` via `with_defaults()`) provides built-in strategies:

| Strategy | Description |
|----------|-------------|
| `vector` | Pure vector similarity search |
| `mmr` | Maximum marginal relevance for diversity |

Hybrid search (vector + keyword) is enabled at the vector-store level via the `use_hybrid_search` config option, not as a retrieval strategy.

Reranking is handled by `RerankingStrategyProtocol` implementations registered in `RerankingStrategyRegistry`:

```python
from lexigram.ai.rag import RetrievalStrategyRegistry

registry = RetrievalStrategyRegistry.with_defaults()
strategy = registry.get("mmr")
```

---

## 7. Testing

Use `RAGModule.stub()` for isolated tests:

```python
from lexigram import Application
from lexigram.ai.rag import RAGModule
from lexigram.contracts.ai.rag import RAGPipelineProtocol


async def test_pipeline_resolves() -> None:
    async with Application.boot(modules=[RAGModule.stub()]) as app:
        pipeline = await app.container.resolve(RAGPipelineProtocol)
        assert pipeline is not None
```

:::caution
The stub uses in-memory storage and a mock embedding provider. Results are deterministic but not grounded in real data.
:::

---

## Next Steps

- [Vector Stores](/guides/vector-stores/) — configuring pgvector, Qdrant, Pinecone, or in-memory backends
- [AI Agents](/guides/ai-agents/) — connecting RAG to agent tool use
- [AI Memory](/guides/ai-memory/) — episodic and semantic memory for conversation context
- [Dependency Injection](/fundamentals/dependency-injection/) — binding protocols to implementations
- [`lexigram-ai-rag` package](/packages/lexigram-ai-rag/) — HyDE, reranking, evaluation, reasoning
